from __future__ import annotations
import sys, os, json
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Local imports
from rag.embedder import Embedder
from rag.vector_store import get_client, get_or_create_collection
from rag.clinical_extractor import extract_patient_summary
from app.validators import validate_and_normalize
from app.justification import build_justification_letter

OUT_DIR = ROOT / "data" / "finetune"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "pa_examples.jsonl"

def retrieve(question: str, top_k: int = 3):
    client = get_client()
    col = get_or_create_collection(client, name="policies")
    emb = Embedder()
    q = emb.embed_texts([question])
    res = col.query(query_embeddings=q, n_results=top_k)
    chunks = []
    for i in range(len(res["ids"][0])):
        chunks.append({
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
        })
    return chunks

def make_row(note_path: Path, service="I-CGM"):
    note = note_path.read_text()
    summary_raw = extract_patient_summary(note)
    summary, _ = validate_and_normalize(summary_raw)
    passages = retrieve("I-CGM coverage medical necessity criteria and documentation requirements", top_k=3)

    # Bootstrap: use current template letter as target output
    letter = build_justification_letter(
        summary, True, [], [{"document": p["text"], "metadata": p["metadata"]} for p in passages]
    )

    return {
        "instruction": f"Write a prior authorization medical necessity letter for {service}.",
        "input": {
            "patient_summary": summary,
            "policy_passages": [{"text": p["text"]} for p in passages],
            "requested_service": service
        },
        "output": letter
    }

def main():
    notes_dir = ROOT / "data" / "examples"
    txts = sorted(notes_dir.glob("*.txt"))
    if not txts:
        print(f"⚠️ No notes found in {notes_dir}. Add .txt notes and re-run.")
        return

    with open(OUT_PATH, "w") as f:
        for p in txts:
            row = make_row(p)
            f.write(json.dumps(row) + "\n")
            print("added:", p.name)

    print("✅ wrote:", OUT_PATH)

if __name__ == "__main__":
    main()
