from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path
from app.hf_llm import get_json_from_text, jsonify_stream, preprocess_text
import json, re , traceback

app = FastAPI()

# 👇 Allow your frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add more if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Prompt(BaseModel):
    text: str

# Single file JSONifdication
@app.post("/txt2json")
async def txt2json(file: str = Query(...)):
    RAW_TXT_DIR = Path("/app/knowledge/txt")
    txt_path = RAW_TXT_DIR / file
    JSON_OUTPUT_DIR = Path("/app/knowledge/Json")
    json_path = JSON_OUTPUT_DIR / (txt_path.stem + ".json")

    if not txt_path.exists():
        return JSONResponse({"error": f"File '{file}' not found"}, status_code=404)

    try:
        raw_text = txt_path.read_text(encoding="utf-8").strip()
        if not raw_text or len(raw_text) < 50:
            return JSONResponse({"error": "File is empty or too short"}, status_code=400)

        # Optional: if you have a cleaning step
        clean_text = preprocess_text(raw_text)

        if len(clean_text) < 100:
            return JSONResponse({"error": "File contains no usable content after cleaning"}, status_code=400)

        json_data = get_json_from_text(clean_text)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        return {"status": f"✅ Saved JSON to {json_path.name}"}

    except Exception as e:
        tb = traceback.format_exc().replace("\n", " | ")
        print(f"[ERROR] {txt_path.name}: {e}\n{tb}")
        return JSONResponse({"error": f"Exception during processing: {str(e)}"}, status_code=500)


@app.get("/batch-txt2json")
async def batch_txt2json():
    return StreamingResponse(jsonify_stream(), media_type="text/event-stream")


@app.get("/jsonify/stream")
def stream_jsonify():
    return StreamingResponse(jsonify_stream(), media_type="text/event-stream")

@app.post("/jsonify-one", response_class=JSONResponse)
def jsonify_one(file: str = Query(...)):
    RAW_TXT_DIR = Path("/app/knowledge/txt")
    JSON_OUTPUT_DIR = Path("/app/knowledge/Json")
    file_path = RAW_TXT_DIR / file
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    raw_text = file_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return JSONResponse({"error": "File is empty"}, status_code=400)

    try:
        json_data = get_json_from_text(raw_text)
        out_path = JSON_OUTPUT_DIR / (file_path.stem + ".json")
        out_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
        return {"status": "✅ JSON saved", "file": out_path.name}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

