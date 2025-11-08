from __future__ import annotations
from typing import List, Dict

def _split_text(text: str, max_tokens: int = 600, overlap: int = 100) -> List[str]:
    """
    Very simple splitter by characters (proxy for tokens). 
    We’ll refine later with token-aware splitting if needed.
    """
    # Convert token-ish to chars (rough heuristic: 1 token ~ 4 chars)
    max_len = max_tokens * 4
    ov_len = overlap * 4

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_len, n)
        chunk = text[start:end]
        chunks.append(chunk.strip())
        if end == n:
            break
        start = max(0, end - ov_len)
    return [c for c in chunks if c]

def chunk_pages(pages: List[Dict], max_tokens: int = 600, overlap: int = 100) -> List[Dict]:
    """
    Input: list of {text, page, source}
    Output: list of chunks {id, text, metadata}
    """
    out = []
    idx = 0
    for p in pages:
        parts = _split_text(p["text"], max_tokens=max_tokens, overlap=overlap)
        for j, part in enumerate(parts):
            out.append({
                "id": f"{p['source']}::p{p['page']}::c{j}",
                "text": part,
                "metadata": {
                    "source": p["source"],
                    "page": p["page"],
                    "chunk_index": j
                }
            })
            idx += 1
    return out
