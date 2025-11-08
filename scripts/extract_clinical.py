from __future__ import annotations
import sys, os, json
from pathlib import Path

# Make project imports work
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rag.clinical_extractor import extract_patient_summary
from app.validators import validate_and_normalize

def main(note_path: str = "data/examples/note1.txt"):
    p = ROOT / note_path
    if not p.exists():
        print(f"⚠️  Note file not found: {p}")
        sys.exit(1)

    text = p.read_text()
    print("🧾 Extracting structured summary from note…")
    summary = extract_patient_summary(text)
    summary_norm, errors = validate_and_normalize(summary)

    out_dir = ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (Path(note_path).stem + ".summary.json")
    out_path.write_text(json.dumps(summary_norm, indent=2))
    print(f"✅ Saved: {out_path}")

    if errors:
        print("\n⚠️ Validation issues:")
        for e in errors:
            print(" -", e)
    else:
        print("\n✅ Validation passed.")

    print("\nPreview:")
    print(json.dumps(summary_norm, indent=2))

if __name__ == "__main__":
    main()
