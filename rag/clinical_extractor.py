from __future__ import annotations
import os, json, re
from typing import Any, Dict, List
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# Optional import - avoid circular dependency for Streamlit
try:
    from app.schemas import PatientSummary
    HAS_SCHEMAS = True
except ImportError:
    HAS_SCHEMAS = False
    PatientSummary = None

SYSTEM_PROMPT = """You are a clinical information extractor.
Extract a structured patient summary from the provided clinical note.
Return STRICT JSON ONLY that matches this schema:

{
  "patient_id": "string or null",
  "age": int or null,
  "sex": "male|female|other|unknown|null",
  "diagnoses": [{"code_system":"ICD-10|SNOMED|null","code":"string|null","description":"string|null"}],
  "labs": [{"name":"string","value": float,"unit":"string|null","collected_date":"YYYY-MM-DD|null"}],
  "meds": [{"name":"string","dose":"string|null","route":"string|null","frequency":"string|null","start_date":"YYYY-MM-DD|null","end_date":"YYYY-MM-DD|null","status":"string|null"}],
  "vitals": [{"name":"string","value": float,"unit":"string|null","measured_date":"YYYY-MM-DD|null"}],
  "note_date":"YYYY-MM-DD|null"
}

Rules:
- If a field is unknown, use null (not empty strings).
- Parse numeric lab values into 'value' (float) and 'unit'.
- Prefer ICD-10 codes for diagnoses when present.
- Dates should be ISO (YYYY-MM-DD) if present.
- Output ONLY JSON. No explanations.
"""

# ---------- LLM CONFIG ----------
def _configure_genai():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing. Add it to .env")
    genai.configure(api_key=api_key)

def _get_model_name() -> str:
    # Allow override via env; default to a light, widely available model.
    return os.getenv("GEMINI_MODEL_GEN", "models/gemini-1.5-flash")

def _get_model():
    _configure_genai()
    return genai.GenerativeModel(_get_model_name())

# ---------- FALLBACK (no-LLM) REGEX EXTRACTOR ----------
def _regex_extract(note_text: str) -> Dict[str, Any]:
    """Very simple, deterministic parser to unblock the pipeline when LLM quota is 0."""
    # patient_id
    m_id = re.search(r"\bMRN\s*([A-Za-z0-9\-]+)", note_text)
    patient_id = m_id.group(1) if m_id else None
    # sex
    m_sex = re.search(r"\bSex:\s*([A-Za-z])", note_text, re.I)
    sex = {"m":"male","f":"female"}.get((m_sex.group(1).lower() if m_sex else ""), None)
    # age: not always present; skip
    age = None
    # diagnoses: pull ICD-10 like E11.65
    diags = []
    for m in re.finditer(r"\b([A-TV-Z][0-9][0-9AB](?:\.[0-9A-Za-z]{1,4})?)\b", note_text):
        code = m.group(1)
        diags.append({"code_system":"ICD-10","code":code,"description":None})
    if not diags:
        # crude text match
        if re.search(r"type\s*2\s*diabetes", note_text, re.I):
            diags.append({"code_system":None,"code":None,"description":"Type 2 diabetes mellitus"})
    # labs: HbA1c and fasting glucose examples
    labs: List[Dict[str, Any]] = []
    m_a1c = re.search(r"(HbA1c|A1C|Hemoglobin A1c)[:\s]*([0-9]+(?:\.[0-9]+)?)\s*%?(?:.*?(\d{4}-\d{2}-\d{2}))?", note_text, re.I)
    if m_a1c:
        labs.append({"name":"HbA1c","value":float(m_a1c.group(2)),"unit":"%","collected_date":(m_a1c.group(3) or None)})
    m_glu = re.search(r"(Fasting glucose)[:\s]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dL)?(?:.*?(\d{4}-\d{2}-\d{2}))?", note_text, re.I)
    if m_glu:
        labs.append({"name":"Fasting glucose","value":float(m_glu.group(2)),"unit":(m_glu.group(3) or "mg/dL"),"collected_date":(m_glu.group(4) or None)})
    # meds: look for insulin / metformin lines
    meds: List[Dict[str, Any]] = []
    for line in note_text.splitlines():
        if re.search(r"\bmetformin\b", line, re.I) or re.search(r"\binsulin\b|\bglargine\b|\baspart\b|\blispro\b", line, re.I):
            meds.append({"name":line.strip(), "dose":None,"route":None,"frequency":None,"start_date":None,"end_date":None,"status":"active"})
    # vitals: optional
    vitals: List[Dict[str, Any]] = []
    m_bp = re.search(r"\bBP\s*([0-9]{2,3})/([0-9]{2,3})", note_text)
    if m_bp:
        vitals.append({"name":"BP_systolic","value":float(m_bp.group(1)),"unit":"mmHg"})
        vitals.append({"name":"BP_diastolic","value":float(m_bp.group(2)),"unit":"mmHg"})
    m_wt = re.search(r"\bweight\s*([0-9]+(?:\.[0-9]+)?)\s*kg", note_text, re.I)
    if m_wt:
        vitals.append({"name":"Weight","value":float(m_wt.group(1)),"unit":"kg"})
    m_ht = re.search(r"\bheight\s*([0-9]+(?:\.[0-9]+)?)\s*cm", note_text, re.I)
    if m_ht:
        vitals.append({"name":"Height","value":float(m_ht.group(1)),"unit":"cm"})

    # note date
    m_nd = re.search(r"Date of service:\s*(\d{4}-\d{2}-\d{2})", note_text)
    note_date = m_nd.group(1) if m_nd else None

    data = {
        "patient_id": patient_id,
        "age": age,
        "sex": sex,
        "diagnoses": diags,
        "labs": labs,
        "meds": meds,
        "vitals": vitals,
        "note_date": note_date,
    }
    
    # Validate with pydantic if available, otherwise return as-is
    if HAS_SCHEMAS and PatientSummary:
        summary = PatientSummary.model_validate(data)
        return json.loads(summary.model_dump_json())
    else:
        return data

# ---------- PUBLIC API ----------
def extract_patient_summary(note_text: str) -> Dict[str, Any]:
    """
    Try LLM extraction (Gemini). If quota is exhausted or unavailable, fall back to
    a deterministic regex extractor so the pipeline keeps moving.
    """
    try:
        model = _get_model()
        resp = model.generate_content(
            SYSTEM_PROMPT + "\n\nCLINICAL NOTE:\n" + note_text,
            generation_config={"response_mime_type": "application/json"},
        )
        text = resp.text or "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{"); end = text.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(text[start:end+1])
            else:
                raise
        
        # Validate with pydantic if available, otherwise return as-is
        if HAS_SCHEMAS and PatientSummary:
            summary = PatientSummary.model_validate(data)
            return json.loads(summary.model_dump_json())
        else:
            return data
            
    except ResourceExhausted:
        # Quota exhausted → fallback to regex
        return _regex_extract(note_text)
    except Exception:
        # Any other transient issue → fallback too (you can log if desired)
        return _regex_extract(note_text)