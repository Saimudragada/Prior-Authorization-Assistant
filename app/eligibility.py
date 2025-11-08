from __future__ import annotations
from typing import Dict, Any, List, Tuple

INSULIN_KEYWORDS = {"insulin", "glargine", "aspart", "lispro"}
METFORMIN_KEYWORDS = {"metformin"}
A1C_NAMES = {"hba1c", "a1c", "hemoglobin a1c"}

def _has_diabetes_dx(summary: Dict[str, Any]) -> bool:
    for d in summary.get("diagnoses", []):
        code = (d.get("code") or "").upper()
        if code.startswith("E10") or code.startswith("E11"):
            return True
        desc = (d.get("description") or "").lower()
        if "type 1 diabetes" in desc or "type 2 diabetes" in desc:
            return True
    return False

def _get_a1c(summary: Dict[str, Any]) -> float | None:
    for lab in summary.get("labs", []):
        if (lab.get("name") or "").lower().strip() in A1C_NAMES:
            try:
                return float(lab.get("value"))
            except Exception:
                pass
    return None

def _on_insulin(summary: Dict[str, Any]) -> bool:
    for m in summary.get("meds", []):
        n = (m.get("name") or "").lower()
        if any(k in n for k in INSULIN_KEYWORDS):
            status = (m.get("status") or "active").lower()
            if status in ("active", "current", "ongoing"):
                return True
    return False

def _has_antidiabetic(summary: Dict[str, Any]) -> bool:
    for m in summary.get("meds", []):
        n = (m.get("name") or "").lower()
        if any(k in n for k in (INSULIN_KEYWORDS | METFORMIN_KEYWORDS)):
            status = (m.get("status") or "active").lower()
            if status in ("active", "current", "ongoing"):
                return True
    return False

def evaluate_icgm(summary: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Demo rules (not medical advice):
    - Diabetes dx present (ICD-10 E10/E11)
    - HbA1c ≥ 8.5% OR on insulin
    - At least one active anti-diabetic medication (insulin/metformin)
    """
    missing: List[str] = []

    if not _has_diabetes_dx(summary):
        missing.append("Diabetes diagnosis (ICD-10 E10/E11).")

    a1c = _get_a1c(summary)
    insulin = _on_insulin(summary)
    if a1c is None and not insulin:
        missing.append("Recent HbA1c value OR active insulin therapy.")
    else:
        if a1c is not None and a1c < 8.5 and not insulin:
            missing.append("HbA1c ≥ 8.5% or active insulin therapy.")

    if not _has_antidiabetic(summary):
        missing.append("At least one active anti-diabetic medication (e.g., insulin or metformin).")

    return (len(missing) == 0, missing)
