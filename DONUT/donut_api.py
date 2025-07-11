# donut_api.py (inside /donut)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from donut_extractor import LayoutLMv3Extractor
import os, json
from pathlib import Path

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

@app.post("/trigger/jsonify-pdf/{filename}")
async def jsonify_pdf(filename: str):
    input_path = os.path.join("../knowledge/raw", filename)
    output_path = os.path.join("../knowledge/testJson", Path(filename).stem + ".json")

    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        result = extractor.extract(input_path)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return {"filename": filename, "json": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
