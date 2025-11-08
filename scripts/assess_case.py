from __future__ import annotations
import sys, os, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rag.embedder import Embedder
from rag.vector_store import get_client, get_or_create_collection
from rag.clinical_extractor import extract_patient_summary
from app.validators import validate_and_normalize
from app.eligibility import evaluate_icgm
from app.justification import build_justification_letter

def _retrieve_policy(question: str, top_k: int = 5):
    client = get_client()
    col = get_or_create_collection(client, name="policies")
    embedder = Embedder()
    q_emb = embedder.embed_texts([question])
    res = col.query(query_embeddings=q_emb, n_results=top_k)
    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "document": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="data/examples/note1.txt")
    ap.add_argument("--summary-json", default=None)
    ap.add_argument("--question", default="I-CGM coverage medical necessity criteria and documentation requirements")
    args = ap.parse_args()

    if args.summary_json:
        data = json.loads(Path(args.summary_json).read_text())
    else:
        note_path = ROOT / args.note
        if not note_path.exists():
            print(f"⚠️  Note not found: {note_path}")
            sys.exit(1)
        print("🧾 Extracting patient summary…")
        raw = extract_patient_summary(note_path.read_text())
        data, _ = validate_and_normalize(raw)

    print("🔎 Retrieving relevant policy passages…")
    hits = _retrieve_policy(args.question, top_k=5)

    print("✅ Evaluating eligibility rules (demo I-CGM)…")
    meets, missing = evaluate_icgm(data)
    letter = build_justification_letter(data, meets, missing, hits)

    out_dir = ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "case.summary.json").write_text(json.dumps(data, indent=2))
    (out_dir / "case.decision.json").write_text(json.dumps({"meets_criteria": meets, "missing_information": missing}, indent=2))
    (out_dir / "case.justification.txt").write_text(letter)

    print("\n🎉 Saved:")
    print(f" - {out_dir/'case.summary.json'}")
    print(f" - {out_dir/'case.decision.json'}")
    print(f" - {out_dir/'case.justification.txt'}")

    print("\n--- Justification Preview ---\n")
    print(letter)

if __name__ == "__main__":
    main()
