from fastapi import FastAPI
from pydantic import BaseModel
from app.hf_llm import get_json_from_text

app = FastAPI()

class Prompt(BaseModel):
    text: str

@app.post("/txt2json")
async def txt2json(prompt: Prompt):
    result = get_json_from_text(prompt.text)
    return result