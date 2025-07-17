# This script uses SmolLM3-3B locally via Transformers to convert raw .txt files into structured JSON.

import os
import re
import json
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Constants
RAW_TXT_DIR = Path("/app/knowledge/raw")
JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load SmolLM3-3B model locally
MODEL_NAME = "HuggingFaceTB/SmolLM3-3B"
#DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEVICE = "cpu"  # Force CPU for compatibility
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE)

# Extract JSON block
def extract_first_json_block(text: str) -> str:
    match = re.search(r"\{[\s\S]*?\}", text)
    if match:
        return match.group(0)
    else:
        raise ValueError("No JSON block found in output.")

# Inference using local SmolLM3-3B
def get_json_from_text(text: str):
    prompt = """You are a JSON generator. Convert the following text into compact, valid JSON with no extra commentary.

ONLY return valid JSON. Do not explain anything.

Input text:
""" + text[:4000]

    try:
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([formatted_prompt], return_tensors="pt").to(DEVICE)
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.2,
            do_sample=False
        )
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True)
        json_candidate = extract_first_json_block(response)
        return json.loads(json_candidate)
    except Exception as e:
        return {"error": str(e), "raw_output": response if 'response' in locals() else None}

# Batch processor
def convert_txt_to_json(txt_path, output_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_text = f.read().strip()

    if not raw_text:
        print(f"[SKIPPED] Empty file: {txt_path.name}")
        return

    print(f"[INFO] Processing {txt_path.name} → {output_path.name}")

    result = get_json_from_text(raw_text)
    if isinstance(result, dict):
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(result, out_f, indent=2, ensure_ascii=False)
        print(f"[SAVED] JSON → {output_path.name}")
    else:
        print(f"[ERROR] Invalid result structure for {txt_path.name}")

# Batch entry point

def batch_txt_to_json():
    txt_files = list(RAW_TXT_DIR.glob("*.txt"))
    print(f"[INFO] Found {len(txt_files)} .txt files to convert.")

    for txt_file in txt_files:
        json_file = JSON_OUTPUT_DIR / (txt_file.stem + ".json")
        convert_txt_to_json(txt_file, json_file)

if __name__ == "__main__":
    batch_txt_to_json()
