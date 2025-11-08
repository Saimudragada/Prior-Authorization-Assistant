from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

def get_client(persist_dir: str | None = None):
    persist_dir = persist_dir or os.getenv("CHROMA_DIR", ".chroma")
    os.makedirs(persist_dir, exist_ok=True)
    # Silence telemetry noise
    os.environ.setdefault("CHROMA_TELEMETRY_IMPLEMENTATION", "none")
    os.environ.setdefault("CHROMA_ANONYMIZED_TELEMETRY", "False")

    client = chromadb.Client(Settings(
        allow_reset=True,
        is_persistent=True,
        persist_directory=persist_dir,
        anonymized_telemetry=False,
    ))
    return client

def get_or_create_collection(client, name: str = "policies"):
    # Dimension is inferred on first add; keep same collection name for consistency
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )

def add_documents(collection, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]], embeddings: List[List[float]]):
    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

def query(collection, text: str, n_results: int = 5, *, embedder=None):
    """
    Query using the SAME embedder as indexing to avoid dimension mismatches.
    If `embedder` is provided, we send `query_embeddings` instead of `query_texts`.
    """
    if embedder is None:
        # Fallback (may trigger Chroma's default 384-dim model; not recommended)
        return collection.query(query_texts=[text], n_results=n_results)

    q_emb = embedder.embed_texts([text])  # shape: [1, dim]
    return collection.query(query_embeddings=q_emb, n_results=n_results)
