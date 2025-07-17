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