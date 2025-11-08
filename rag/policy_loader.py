from __future__ import annotations
import fitz  # PyMuPDF
from typing import List, Dict

def load_pdf_with_pages(path: str) -> List[Dict]:
    """
    Returns a list of dicts: { 'text': str, 'page': int, 'source': str }
    One item per page, preserving page numbers (0-based).
    """
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        # Normalize whitespace a bit
        text = "\n".join(line.rstrip() for line in text.splitlines())
        pages.append({"text": text, "page": i, "source": path})
    doc.close()
    return pages
