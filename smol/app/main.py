from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.hf_llm import get_json_from_text, jsonify_stream

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

@app.post("/txt2json")
async def txt2json(prompt: Prompt):
    result = get_json_from_text(prompt.text)
    return result

@app.post("/batch-txt2json")
async def batch_txt2json():
    return StreamingResponse(jsonify_stream(), media_type="text/event-stream")

@app.get("/jsonify/stream")
def stream_jsonify():
    return StreamingResponse(jsonify_stream(), media_type="text/event-stream")

