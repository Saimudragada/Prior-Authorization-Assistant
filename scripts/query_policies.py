from __future__ import annotations
import sys
from pathlib import Path

# --- Ensure project imports work no matter where you run this from ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# --- Load .env explicitly from project root ---
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rag.vector_store import get_client, get_or_create_collection, query
from rag.embedder import Embedder

def main():
    client = get_client()
    col = get_or_create_collection(client, name="policies")
    embedder = Embedder()  # Gemini text-embedding-004

    try:
        question = input("Type a policy question (e.g., HbA1c threshold for CGM): ").strip()
    except KeyboardInterrupt:
        print("\nBye!")
        return

    if not question:
        print("No question entered.")
        return

    res = query(col, question, n_results=3, embedder=embedder)  # <-- use our embedder
    print("\nTop matches:\n")
    if not res or not res.get("ids") or not res["ids"][0]:
        print("No results found.")
        return

    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i]
        doc = res["documents"][0][i][:500].replace("\n", " ")
        print(f"- source: {meta.get('source')}  page: {meta.get('page')}  chunk: {meta.get('chunk_index')}")
        print(f"  excerpt: {doc}…\n")

if __name__ == "__main__":
    main()
