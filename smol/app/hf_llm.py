# In main.py or your FastAPI backend file

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import os, json
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re

router = APIRouter()

RAW_TXT_DIR = Path("/app/knowledge/raw")
JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load model only once (no multiprocessing here for SSE)
MODEL_NAME = "HuggingFaceTB/SmolLM3-3B"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cpu")

def extract_first_json_block(text: str) -> str:
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found.")
    brace_count = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]
    raise ValueError("Unbalanced JSON.")

def jsonify_stream():
    txt_files = list(RAW_TXT_DIR.glob("*.txt"))
    if not txt_files:
        yield "data: No .txt files found.\n\n"
        return

    yield f"data: Found {len(txt_files)} file(s).\n\n"

    for txt_path in txt_files:
        json_path = JSON_OUTPUT_DIR / (txt_path.stem + ".json")


        try:
            raw_text = txt_path.read_text(encoding="utf-8").strip()
            if not raw_text:
                yield f"data: [SKIP] {txt_path.name} is empty.\n\n"
                continue

            yield f"data: [START] Processing {txt_path.name}...\n\n"

            prompt = (
                "You are a JSON generator. Convert the following text into compact, valid JSON.\n\n"
                "ONLY return valid JSON.\n\nInput text:\n" + raw_text[:4000]
            )

            messages = [{"role": "user", "content": prompt}]
            formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer([formatted_prompt], return_tensors="pt").to("cpu")
            outputs = model.generate(**inputs, max_new_tokens=2048, temperature=0.2, do_sample=False)
            generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
            response = tokenizer.decode(generated_ids, skip_special_tokens=True)
            response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
            json_data = json.loads(extract_first_json_block(response))

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            yield f"data: [DONE] Saved {json_path.name}\n\n"

        except Exception as e:
            yield f"data: [ERROR] {txt_path.name}: {str(e)}\n\n"

    yield "data: [COMPLETE] All files processed.\n\n"

@router.get("/jsonify/stream")
def stream_jsonify():
    return StreamingResponse(jsonify_stream(), media_type="text/event-stream")
