import sys, platform
import fitz  # PyMuPDF
import chromadb
import pydantic
import fastapi
import pandas as pd
import numpy as np

print("Python:", sys.version)
print("Platform:", platform.platform())
print("PyMuPDF:", fitz.__doc__.splitlines()[0] if fitz.__doc__ else "OK")
print("ChromaDB:", chromadb.__version__)
print("Pydantic:", pydantic.__version__)
print("FastAPI:", fastapi.__version__)
print("Pandas:", pd.DataFrame({'ok':[1]}))
print("✅ Smoke test passed.")
