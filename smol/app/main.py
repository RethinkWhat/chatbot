from fastapi import FastAPI
from pydantic import BaseModel
from app.hf_llm import get_json_from_text,batch_txt_to_json

app = FastAPI()

class Prompt(BaseModel):
    text: str

@app.post("/txt2json")
async def txt2json(prompt: Prompt):
    """Single prompt-to-JSON conversion."""
    result = get_json_from_text(prompt.text)
    return result

@app.post("/batch-txt2json")
async def batch_txt2json():
    """
    Run batch conversion of all .txt files in knowledge/txt,
    splitting into token-aware chunks and saving to testJson.
    """
    print("[INFO] Starting batch conversion of .txt files to JSON...")
    batch_txt_to_json()
    return {"status": "✅ Batch conversion completed."}

def jsonify_stream():
    txt_files = list(RAW_TXT_DIR.glob("*.txt"))
    total = len(txt_files)
    yield f"data: Starting JSONification of {total} files...\n\n"
    
    for i, txt_file in enumerate(txt_files, 1):
        json_file = JSON_OUTPUT_DIR / (txt_file.stem + ".json")
        try:
            result = get_json_from_text(txt_file.read_text(encoding="utf-8"))
            json_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            yield f"data: ✅ [{i}/{total}] {txt_file.name} processed.\n\n"
        except Exception as e:
            yield f"data: ❌ [{i}/{total}] Error in {txt_file.name}: {str(e)}\n\n"
        time.sleep(0.1)

    yield "data: ✅ All files processed.\n\n"

@app.get("/jsonify/stream")
async def stream_jsonify():
    return StreamingResponse(jsonify_stream(), media_type="text/event-stream")