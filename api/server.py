from __future__ import annotations
import os, json
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

from fastapi import FastAPI
from pydantic import BaseModel, Field

# --- project path + env ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# --- project imports ---
from rag.embedder import Embedder
from rag.vector_store import get_client, get_or_create_collection
from rag.clinical_extractor import extract_patient_summary
from app.validators import validate_and_normalize
from app.eligibility import evaluate_icgm
from app.justification import build_justification_letter

app = FastAPI(title="PA Assistant API", version="0.1.0")

# ---------- Pydantic IO models ----------
class AssessRequest(BaseModel):
    note_text: Optional[str] = Field(default=None, description="Full clinical note text.")
    summary_json: Optional[Dict[str, Any]] = Field(default=None, description="Provide pre-extracted patient summary instead of raw note.")

class Citation(BaseModel):
    source: str
    page: int
    excerpt: str

class Decision(BaseModel):
    meets_criteria: bool
    missing_information: List[str]

class AssessResponse(BaseModel):
    summary: Dict[str, Any]
    decision: Decision
    citations: List[Citation]
    justification_letter: str

# ---------- Helpers ----------
def _retrieve_policy(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    client = get_client()
    col = get_or_create_collection(client, name="policies")
    embedder = Embedder()  # Gemini embeddings (text-embedding-004)
    q_emb = embedder.embed_texts([question])
    res = col.query(query_embeddings=q_emb, n_results=top_k)

    out: List[Dict[str, Any]] = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "document": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
        })
    return out

def _format_citations(hits: List[Dict[str, Any]]) -> List[Citation]:
    cits: List[Citation] = []
    for h in hits:
        meta = h.get("metadata", {})
        src = meta.get("source", "?")
        pg = meta.get("page", 0)  # 0-indexed
        excerpt = (h.get("document","")[:300].replace("\n"," ") + "…") if h.get("document") else ""
        cits.append(Citation(source=src, page=int(pg) + 1, excerpt=excerpt))
    return cits

# ---------- Routes ----------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/assess", response_model=AssessResponse)
def assess(req: AssessRequest):
    # 1) Get the patient summary (either provided or extracted)
    if req.summary_json:
        raw_summary = req.summary_json
    else:
        if not req.note_text:
            return {"detail": "Provide either note_text or summary_json"}  # FastAPI will 500 if we don't return right shape; raise instead:
        raw_summary = extract_patient_summary(req.note_text)

    summary, _errors = validate_and_normalize(raw_summary)

    # 2) Retrieve relevant policy chunks
    hits = _retrieve_policy("I-CGM coverage medical necessity criteria and documentation requirements", top_k=5)

    # 3) Evaluate eligibility
    meets, missing = evaluate_icgm(summary)

    # 4) Build letter
    letter = build_justification_letter(summary, meets, missing, hits)

    # 5) Respond
    decision = Decision(meets_criteria=meets, missing_information=missing)
    citations = _format_citations(hits)

    return AssessResponse(
        summary=summary,
        decision=decision,
        citations=citations,
        justification_letter=letter
    )

# Optional: simple policy query endpoint
class QueryReq(BaseModel):
    question: str

class QueryResp(BaseModel):
    citations: List[Citation]

@app.post("/query-policies", response_model=QueryResp)
def query_policies(req: QueryReq):
    hits = _retrieve_policy(req.question, top_k=5)
    return QueryResp(citations=_format_citations(hits))
