# donut_api.py (inside /donut)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from train_donut import train_donut_model
from donut_extractor import LayoutLMv3Extractor
import os, json, io , contextlib, traceback
from pathlib import Path
import logging, subprocess
from tqdm import tqdm
from pdf2image import convert_from_path

logging.basicConfig(level=logging.INFO)
from datetime import datetime
from inference import run_inference_batch

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

@app.post("/train/donut")
def train_donut():
    result = train_donut_model()
    return {
        "status": result.get("status", "❌ Unknown training status"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("error", "")
    }

@app.post("/prepare/training-data")
def prepare_training_data():
    try:
        PDF_DIR = Path("/app/datasets/pdfs")
        JSON_DIR = Path("/app/datasets/labels")
        IMAGE_DIR = Path("/app/datasets/images")
        JSONL_PATH = Path("/app/training.jsonl")

        IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        entries = []

        for json_file in tqdm(JSON_DIR.glob("*.json"), desc="📄 Building training.jsonl"):
            base = json_file.stem
            pdf_file = PDF_DIR / f"{base}.pdf"

            if not pdf_file.exists():
                print(f"⚠️ Missing PDF for {json_file.name}, skipping.")
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    label = json.load(f)
                except Exception as e:
                    print(f"⚠️ Invalid JSON in {json_file.name}: {e}")
                    continue

            try:
                pages = convert_from_path(str(pdf_file), dpi=150)
            except Exception as e:
                print(f"⚠️ Failed to convert {pdf_file.name}: {e}")
                continue

            for i, page in enumerate(pages):
                image_filename = f"{base}_page{i+1}.png"
                image_path = IMAGE_DIR / image_filename
                page.save(image_path, format="PNG")

                entries.append({
                    "image": str(image_path.resolve()),
                    "ground_truth": json.dumps(label, ensure_ascii=False)
                })

        with open(JSONL_PATH, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return JSONResponse(content={"status": f"✅ training.jsonl created with {len(entries)} entries."})

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "❌ Failed to prepare training data.",
            "error": str(e)
        })

@app.post("/jsonify")
async def jsonify_pdfs():
    input_dir = Path("/app/knowledge/raw")
    output_dir = Path("/app/knowledge/testJson")

    processed_files = run_inference_batch(input_dir, output_dir)

    return {
        "status": "success",
        "files": processed_files,
        "count": len(processed_files)
    }