from __future__ import annotations
from typing import Dict, Any, List

def build_justification_letter(
    summary: Dict[str, Any],
    decision: bool,
    missing: List[str],
    retrieved: List[Dict[str, Any]],
) -> str:
    patient = summary.get("patient_id", "Patient")
    sex = summary.get("sex", "unknown")
    age = summary.get("age", "unknown")

    dx = ", ".join(
        f"{(d.get('code') or '')} {(d.get('description') or '')}".strip()
        for d in summary.get("diagnoses", [])
    ) or "N/A"

    a1c = next((lab for lab in summary.get("labs", []) if (lab.get("name","").lower() in {"hba1c","a1c","hemoglobin a1c"})), None)
    a1c_str = f"{a1c.get('value')}{a1c.get('unit') or ''}" if a1c else "N/A"

    meds = ", ".join(m.get("name","") for m in summary.get("meds", [])) or "N/A"

    lines = []
    lines.append("Subject: Prior Authorization Request for Implantable Continuous Glucose Monitor (I-CGM)")
    lines.append("")
    lines.append(f"Patient: {patient} | Sex: {sex} | Age: {age}")
    lines.append(f"Diagnoses: {dx}")
    lines.append(f"Recent HbA1c: {a1c_str}")
    lines.append(f"Current Medications: {meds}")
    lines.append("")

    if decision:
        lines.append("Medical Necessity Rationale:")
        lines.append("- Qualifying diabetes diagnosis with suboptimal control and/or active insulin therapy.")
        lines.append("- Continuous glucose monitoring is medically necessary to improve glycemic management and reduce hypoglycemia risk, consistent with payer policy criteria.")
    else:
        lines.append("Preliminary Assessment (More Information Needed):")
        for m in missing:
            lines.append(f"- {m}")

    if retrieved:
        lines.append("")
        lines.append("Policy Citations (source page):")
        for r in retrieved:
            meta = r.get("metadata", {})
            src = meta.get("source", "?")
            pg = meta.get("page", "?")
            excerpt = (r.get("document","")[:300].replace("\n", " ") + "…") if r.get("document") else ""
            # +1 to humanize page numbers
            lines.append(f"- {src} (p.{(pg or 0)+1}) — {excerpt}")

    lines.append("")
    lines.append("Sincerely,")
    lines.append("Prior Authorization Assistant")
    return "\n".join(lines)
