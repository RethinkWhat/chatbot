# donut_api.py (inside /donut)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from donut_extractor import LayoutLMv3Extractor
import os, json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
from datetime import datetime

app = FastAPI()

# Allow requests from other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the extractor once
extractor = LayoutLMv3Extractor()

@app.get("/list-pdfs")
def list_pdf_files():
    folder = "knowledge/raw"  # Use absolute path (inside container)
    if not os.path.exists(folder):
        raise HTTPException(status_code=500, detail=f"Folder '{folder}' does not exist inside the container.")

    files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    return {"files": files}


@app.post("/trigger/jsonify-pdf/{filename}")
def jsonify_pdf(filename: str):
    pdf_path = os.path.join("knowledge/raw", filename)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not os.path.exists(pdf_path):
        logging.error(f"[{timestamp}] ❌ PDF not found: {filename}")
        raise HTTPException(status_code=404, detail="PDF file not found.")

    logging.info(f"[{timestamp}] 📄 Starting JSONification of: {filename}")

    try:
        result = extractor.extract(pdf_path)
    except Exception as e:
        logging.error(f"[{timestamp}] ❌ Extraction failed for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    output_path = os.path.join("knowledge/testJson", Path(filename).stem + ".json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logging.info(f"[{timestamp}] ✅ JSON saved: {output_path}")
    except Exception as e:
        logging.error(f"[{timestamp}] ❌ Failed to save JSON: {e}")
        raise HTTPException(status_code=500, detail=f"JSON save error: {e}")

    return {"filename": filename, "output": output_path, "json": result}