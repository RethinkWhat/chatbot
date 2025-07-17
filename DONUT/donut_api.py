# donut_api.py (inside /donut)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from train_donut import train_donut_model

import os, json, io , contextlib, traceback
from pathlib import Path
import logging, subprocess
from tqdm import tqdm
from pdf2image import convert_from_path
from train_donut import train_donut_model, classify_document_type,stitch_pdf_to_image


logging.basicConfig(level=logging.INFO)
from datetime import datetime
from DONUT.inference import run_inference_batch

app = FastAPI()
DPI = 200

# Allow requests from other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/list-pdfs")
def list_pdf_files():
    folder = "knowledge/raw"  # Use absolute path (inside container)
    if not os.path.exists(folder):
        raise HTTPException(status_code=500, detail=f"Folder '{folder}' does not exist inside the container.")

    files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    return {"files": files}

@app.post("/train/donut")
#def train_donut(filename):
def train_donut():
# def train_donut_for_file(filename: str):
    #task_type = classify_document_type(filename)
    filenames = ["announcements", "calendar", "program_catalog", "school_info"]
    results = []
    for filename in filenames:
        result = train_donut_model(filename)
        results.append({
            "filename": filename,
            "status": result.get("status", "❌ Unknown training status"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("error", "")
        })
    return {"results": results}

@app.post("/prepare/training-data")
def prepare_all_training_data():
    try:
        BASE_DIR = Path("/app/datasets/types")
        IMAGE_DIR_ROOT = Path("/app/datasets/images")
        JSONL_ROOT = Path("/app/training_jsonl") # This will store the .jsonl files for Donut training
        JSONL_ROOT.mkdir(parents=True, exist_ok=True)

        results = {}

        # Iterate through each document type directory (e.g., ProgCat, AcademicCalendar)
        for task_dir in BASE_DIR.iterdir():
            if not task_dir.is_dir():
                continue

            task_name = task_dir.name # e.g., "ProgCat"
            PDF_DIR = task_dir / "pdfs" # e.g., /app/datasets/types/ProgCat/pdfs
            JSON_DIR = task_dir / "labels" # e.g., /app/datasets/types/ProgCat/labels
            IMAGE_DIR = IMAGE_DIR_ROOT / task_name # e.g., /app/datasets/images/ProgCat
            JSONL_PATH = JSONL_ROOT / f"{task_name}.jsonl" # e.g., /app/training_jsonl/ProgCat.jsonl
            
            IMAGE_DIR.mkdir(parents=True, exist_ok=True) # Create image directory for this task type

            entries = [] # List to store entries for the current task_name's .jsonl file

            # Iterate through each JSON label file for the current task type
            for json_file in tqdm(JSON_DIR.glob("*.json"), desc=f"📄 {task_name}"):
                base = json_file.stem # e.g., "Program_Catalog_Accountancy"
                pdf_file = PDF_DIR / f"{base}.pdf" # e.g., /app/datasets/types/ProgCat/pdfs/Program_Catalog_Accountancy.pdf
                
                if not pdf_file.exists():
                    print(f"⚠️ Missing PDF for {json_file.name}, skipping.")
                    continue

                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        label = json.load(f)
                except Exception as e:
                    print(f"⚠️ Invalid JSON in {json_file.name}: {e}")
                    continue

                try:
                    # --- CALL STITCH_PDF_TO_IMAGE HERE ---
                    stitched_image = stitch_pdf_to_image(pdf_file)
                    
                    # Define a filename for the stitched image
                    stitched_image_filename = f"{base}_stitched.png"
                    stitched_image_path = IMAGE_DIR / stitched_image_filename
                    
                    # Save the stitched image
                    stitched_image.save(stitched_image_path, format="PNG")

                    # Add the entry to the list
                    entries.append({
                        "image": str(stitched_image_path.resolve()), # Path to the saved stitched image
                        "ground_truth": json.dumps(label, ensure_ascii=False)
                    })

                except Exception as e:
                    print(f"⚠️ Failed to stitch or save {pdf_file.name}: {e}")
                    continue

            # Write all entries for the current task type to its .jsonl file
            with open(JSONL_PATH, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            results[task_name] = f"{len(entries)} entries saved to {JSONL_PATH.name}"

        return JSONResponse(content={"status": "✅ All training .jsonl files created", "details": results})

    except Exception as e:
        # Log the full traceback for better debugging in production
        print(f"❌ An error occurred: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={
            "status": "❌ Failed to prepare training data.",
            "error": str(e),
            "traceback": traceback.format_exc() # Include traceback for API response
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