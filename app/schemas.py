from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import date

class Diagnosis(BaseModel):
    code_system: Optional[str] = Field(None, description="e.g., ICD-10, SNOMED")
    code: Optional[str] = Field(None, description="e.g., E11.65")
    description: Optional[str] = None

class Lab(BaseModel):
    name: str
    value: float
    unit: Optional[str] = None
    collected_date: Optional[str] = Field(None, description="ISO date, e.g., 2025-10-25")

class Medication(BaseModel):
    name: str
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = Field(None, description="active, discontinued, etc.")

class Vital(BaseModel):
    name: str
    value: float
    unit: Optional[str] = None
    measured_date: Optional[str] = None

class PatientSummary(BaseModel):
    patient_id: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = Field(None, description="male/female/other/unknown")
    diagnoses: List[Diagnosis] = []
    labs: List[Lab] = []
    meds: List[Medication] = []
    vitals: List[Vital] = []
    note_date: Optional[str] = None

    @field_validator("sex")
    @classmethod
    def normalize_sex(cls, v):
        if not v:
            return v
        v2 = v.strip().lower()
        mapping = {"m": "male", "f": "female"}
        return mapping.get(v2, v2)
