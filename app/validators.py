from __future__ import annotations
from typing import Dict, Any, List, Tuple

SAFE_RANGES = {
    "HbA1c": (3.0, 20.0),   # percent
    "A1C": (3.0, 20.0),
    "Hemoglobin A1c": (3.0, 20.0),
}

UNIT_NORMALIZE = {
    "hba1c": "%",
    "a1c": "%",
    "hemoglobin a1c": "%",
}

def normalize_units(summary: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(summary)
    labs = out.get("labs", [])
    for lab in labs:
        name = (lab.get("name") or "").strip()
        unit = lab.get("unit")
        low_name = name.lower()
        if unit in (None, "", "percent", "Percent", "%"):
            if low_name in UNIT_NORMALIZE:
                lab["unit"] = "%"
        # If no unit but value looks like percent range, assume %
        if not lab.get("unit") and 0.0 < float(lab.get("value", 0)) <= 20.0:
            if any(k.lower() == low_name for k in UNIT_NORMALIZE.keys()):
                lab["unit"] = "%"
    return out

def validate_ranges(summary: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for lab in summary.get("labs", []):
        name = (lab.get("name") or "").strip()
        value = lab.get("value")
        if value is None:
            continue
        if name in SAFE_RANGES:
            lo, hi = SAFE_RANGES[name]
            if not (lo <= float(value) <= hi):
                errors.append(f"Lab '{name}' value {value} out of safe range [{lo}, {hi}].")
    return errors

def required_fields(summary: Dict[str, Any]) -> List[str]:
    errs = []
    if not summary.get("diagnoses"):
        errs.append("At least one diagnosis should be present.")
    return errs

def validate_and_normalize(summary: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    s2 = normalize_units(summary)
    errors = []
    errors += required_fields(s2)
    errors += validate_ranges(s2)
    return s2, errors
