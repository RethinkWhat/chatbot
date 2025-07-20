import os
import re
import json
import time
import torch
import logging
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, current_process, cpu_count
from transformers import AutoTokenizer, AutoModelForCausalLM

# ------------------- Logging Setup -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

# ------------------- Constants -------------------
RAW_TXT_DIR = Path("/app/knowledge/raw")
JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_NAME = "HuggingFaceTB/SmolLM3-3B"

# ------------------- Model Loader (Per Process) -------------------
def load_model_and_tokenizer():
    logging.info("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cpu")
    return tokenizer, model

# ------------------- JSON Extraction Helper -------------------
def extract_first_json_block(text: str) -> str:
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in output.")

    brace_count = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]
    raise ValueError("Unbalanced JSON braces in output.")

# ------------------- Inference -------------------
def get_json_from_text(text: str, tokenizer, model):
    prompt = """You are a JSON generator. Convert the following text into compact, valid JSON with no extra commentary.

ONLY return valid JSON. Do not explain anything.

Input text:
""" + text[:4000]

    try:
        start = time.time()
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([formatted_prompt], return_tensors="pt").to("cpu")

        logging.info(f"[INFO] Tokenization done in {time.time() - start:.2f}s")

        gen_start = time.time()
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=False  # `temperature`/`top_p` will be ignored when sampling is off
        )
        logging.info(f"[INFO] Generation done in {time.time() - gen_start:.2f}s")

        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
        json_candidate = extract_first_json_block(response)
        return json.loads(json_candidate)
    except Exception as e:
        logging.error(f"[EXCEPTION] {e}")
        return {"error": str(e), "raw_output": response if 'response' in locals() else None}

# ------------------- Worker Function -------------------
def process_file(txt_file):
    process_name = current_process().name
    json_file = JSON_OUTPUT_DIR / (txt_file.stem + ".json")

    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()

        if not raw_text:
            logging.info(f"[SKIPPED] Empty file: {txt_file.name}")
            return

        logging.info(f"[{process_name}] Processing {txt_file.name} → {json_file.name}")
        tokenizer, model = load_model_and_tokenizer()
        result = get_json_from_text(raw_text, tokenizer, model)

        with open(json_file, "w", encoding="utf-8") as out_f:
            json.dump(result, out_f, indent=2, ensure_ascii=False)

        logging.info(f"[{process_name}] Saved → {json_file.name}")

    except Exception as e:
        logging.error(f"[{process_name}] Failed on {txt_file.name} with error: {e}")

# ------------------- Main Entrypoint -------------------
def batch_txt_to_json():
    txt_files = list(RAW_TXT_DIR.glob("*.txt"))
    logging.info(f"[INFO] Found {len(txt_files)} .txt files to convert.")

    with Pool(processes=cpu_count()) as pool:
        pool.map(process_file, txt_files)

if __name__ == "__main__":
    batch_txt_to_json()
