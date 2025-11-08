from __future__ import annotations
import os
from typing import List
import google.generativeai as genai

class Embedder:
    """
    Gemini-based embedder (free tier friendly).
    Uses models/text-embedding-004 by default.
    Reads GEMINI_API_KEY from .env or environment.
    """
    def __init__(self, model: str | None = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env (or environment)")
        genai.configure(api_key=api_key)
        self.model = model or "models/text-embedding-004"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in texts:
            resp = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document",
            )
            embeddings.append(resp["embedding"])
        return embeddings
