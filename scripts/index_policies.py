from __future__ import annotations
import sys, os, glob
from pathlib import Path

# --- Make project imports work no matter where you run this from ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# --- Load .env explicitly from project root so keys are always found ---
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rag.policy_loader import load_pdf_with_pages
from rag.chunker import chunk_pages
from rag.embedder import Embedder
from rag.vector_store import get_client, get_or_create_collection, add_documents

def index_directory(pdf_dir: str = "data/raw_policies"):
    pdf_dir_path = ROOT / pdf_dir
    pdfs = sorted(glob.glob(str(pdf_dir_path / "*.pdf")))
    if not pdfs:
        print(f"⚠️  No PDFs found in {pdf_dir_path}. Add policy PDFs and rerun.")
        return

    # Optional: silence Chroma telemetry noise
    os.environ.setdefault("CHROMA_TELEMETRY_IMPLEMENTATION", "none")
    os.environ.setdefault("CHROMA_ANONYMIZED_TELEMETRY", "False")

    client = get_client()
    col = get_or_create_collection(client, name="policies")
    embedder = Embedder()  # uses GEMINI_API_KEY + text-embedding-004

    total_chunks = 0
    for path in pdfs:
        print(f"📄 Processing: {path}")
        pages = load_pdf_with_pages(path)
        chunks = chunk_pages(pages, max_tokens=600, overlap=100)

        if not chunks:
            print("   ⚠️ No text extracted; skipping.")
            continue

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        print(f"   → {len(chunks)} chunks. Embedding…")
        embs = embedder.embed_texts(texts)

        add_documents(col, ids, texts, metadatas, embs)
        total_chunks += len(chunks)
        print(f"   ✅ Indexed {len(chunks)} chunks.")

    print(f"🎉 Done. Total chunks indexed: {total_chunks}")

if __name__ == "__main__":
    index_directory()
