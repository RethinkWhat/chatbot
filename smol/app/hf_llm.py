import json, re, traceback, time
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from datetime import datetime

RAW_TXT_DIR = Path("/app/knowledge/raw")
JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# === Load SmolLMv3 ===
MODEL_NAME = "HuggingFaceTB/SmolLM3-3B"

def load_model():
    if torch.cuda.is_available():
        try:
            print("[INIT] Attempting GPU model load...")
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cuda")
            print("[INFO] Model loaded on GPU")
            return tokenizer, model, torch.device("cuda")
        except Exception as e:
            print(f"[WARN] Failed to load model on GPU: {e}, falling back to CPU...")
    print("[INIT] Loading model on CPU...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cpu")
    return tokenizer, model, torch.device("cpu")

tokenizer, model, DEVICE = load_model()

# === Text Cleaning / Preprocessing ===
def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def filter_relevant_lines(text: str) -> str:
    lines = text.split("\n")
    filtered = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) > 50 or line.endswith("?"):
            filtered.append(line)
    return "\n\n".join(filtered)

def preprocess_text(text: str) -> str:
    return filter_relevant_lines(clean_text(text))

# === Extract clean JSON block ===
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
    print("[WARNING] Unbalanced JSON, returning best-effort block")
    return text[start:]  # fallback to partial

# === Inject metadata ===
def inject_metadata(json_data: dict, source_filename: str) -> dict:
    json_data["_meta"] = {
        "source": source_filename,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    return json_data

# === Call LLM with strict prompt ===
def get_json_from_text(text: str) -> dict:
    formatted_prompt = (
    "You are a JSON generator. Convert the following text into compact, valid JSON.\n\n"
    "ONLY return valid JSON.\n\nInput text:\n" + text[:2000]
    )
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(DEVICE)

    print(f"[DEBUG] Input tensor device: {inputs['input_ids'].device}")
    max_tokens = 2048

    try:
        start_time = time.time()
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.0,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
        duration = time.time() - start_time
        print(f"[TIME] Generation took {duration:.2f} seconds")
        print(f"[DEBUG] Tokens generated: {outputs.shape[-1] - inputs['input_ids'].shape[-1]}")

        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True)
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

        print(f"[DEBUG] Raw LLM output:\n{response[:500]}...\n")

        json_block = extract_first_json_block(response)
        return json.loads(json_block)

    except json.JSONDecodeError as jde:
        print(f"[JSON DECODE ERROR] {jde}\n[RAW OUTPUT] >>> {response[:800]}")
        raise
    except Exception as e:
        print(f"[GEN ERROR] Exception during generation: {e}")
        raise

# === Stream over all .txt files ===
def jsonify_stream():
    txt_files = list(RAW_TXT_DIR.glob("*.txt"))
    if not txt_files:
        yield "data: No .txt files found.\n\n"
        return

    yield f"data: Found {len(txt_files)} file(s).\n\n"

    for txt_path in txt_files:
        json_path = JSON_OUTPUT_DIR / (txt_path.stem + ".json")
        try:
            print(f"[Processing] {txt_path.name}")
            raw = txt_path.read_text(encoding="utf-8").strip()
            if not raw or len(raw) < 50:
                yield f"data: [SKIP] {txt_path.name} is empty or too short.\n\n"
                continue

            cleaned = preprocess_text(raw)
            if len(cleaned) < 100:
                yield f"data: [SKIP] {txt_path.name} contains no usable content.\n\n"
                continue

            yield f"data: [START] Processing {txt_path.name}...\n\n"
            json_data = get_json_from_text(cleaned)
            json_data = inject_metadata(json_data, txt_path.name)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            yield f"data: [DONE] Saved {json_path.name}\n\n"

        except Exception as e:
            tb = traceback.format_exc().replace("\n", " | ")
            print(f"[ERROR] {txt_path.name}: {e}\n{tb}")
            yield f"data: [ERROR] {txt_path.name}: {str(e)}\n\n"

    yield "data: [COMPLETE] All files processed.\n\n"



#======================
#        tiny
# import json, re, traceback
# from pathlib import Path
# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch

# RAW_TXT_DIR = Path("/app/knowledge/raw")
# JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
# JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# # === Load TinyLLaMA ===
# MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cuda" if torch.cuda.is_available() else "cpu")

# DEVICE = next(model.parameters()).device
# print(f"[INFO] Model loaded on device: {DEVICE}")

# # === Text Cleaning / Preprocessing ===
# def clean_text(text: str) -> str:
#     text = text.replace("\r\n", "\n").replace("\r", "\n")
#     text = re.sub(r"\n{3,}", "\n\n", text)
#     text = re.sub(r"[ \t]+", " ", text)
#     return text.strip()

# def filter_relevant_lines(text: str) -> str:
#     lines = text.split("\n")
#     return "\n\n".join(
#         line for line in (l.strip() for l in lines)
#         if line and (len(line) > 50 or line.endswith("?"))
#     )

# def preprocess_text(text: str) -> str:
#     return filter_relevant_lines(clean_text(text))

# # === Extract clean JSON block ===
# def extract_first_json_block(text: str) -> str:
#     start = text.find('{')
#     if start == -1:
#         raise ValueError("No JSON object found.")
#     brace_count = 0
#     for i in range(start, len(text)):
#         if text[i] == '{':
#             brace_count += 1
#         elif text[i] == '}':
#             brace_count -= 1
#             if brace_count == 0:
#                 return text[start:i+1]
#     print("[WARNING] Unbalanced JSON, returning best-effort block")
#     return text[start:]

# # === Call LLM with strict prompt ===
# def get_json_from_text(text: str) -> dict:
#     prompt = (
#         "You are a JSON generator. ONLY return a valid JSON object. "
#         "Do not include any explanation or formatting.\n\n"
#         "Input text:\n" + text[:1500]
#     )

#     inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
#     max_tokens = min(2048, 2048 - inputs["input_ids"].shape[-1])

#     try:
#         outputs = model.generate(
#             **inputs,
#             max_new_tokens=max_tokens,
#             temperature=0.2,
#             do_sample=False,
#             pad_token_id=tokenizer.eos_token_id
#         )
#         generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
#         response = tokenizer.decode(generated_ids, skip_special_tokens=True)
#         response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

#         print(f"[DEBUG] Raw LLM output:\n{response[:500]}...\n")

#         json_block = extract_first_json_block(response)
#         return json.loads(json_block)

#     except json.JSONDecodeError as jde:
#         print(f"[JSON DECODE ERROR] {jde}")
#         raise
#     except Exception as e:
#         print(f"[GEN ERROR] Exception during generation: {e}")
#         raise

# # === Stream over all .txt files ===
# def jsonify_stream():
#     txt_files = list(RAW_TXT_DIR.glob("*.txt"))
#     if not txt_files:
#         yield "data: No .txt files found.\n\n"
#         return

#     yield f"data: Found {len(txt_files)} file(s).\n\n"

#     for txt_path in txt_files:
#         json_path = JSON_OUTPUT_DIR / (txt_path.stem + ".json")
#         try:
#             print(f"[Processing] {txt_path.name}")
#             raw_text = txt_path.read_text(encoding="utf-8").strip()
#             if not raw_text or len(raw_text) < 50:
#                 yield f"data: [SKIP] {txt_path.name} is empty or too short.\n\n"
#                 continue

#             clean_text = preprocess_text(raw_text)
#             if len(clean_text) < 100:
#                 yield f"data: [SKIP] {txt_path.name} contains no usable content.\n\n"
#                 continue

#             yield f"data: [START] Processing {txt_path.name}...\n\n"
#             json_data = get_json_from_text(clean_text)

#             with open(json_path, "w", encoding="utf-8") as f:
#                 json.dump(json_data, f, indent=2, ensure_ascii=False)

#             yield f"data: [DONE] Saved {json_path.name}\n\n"

#         except Exception as e:
#             tb = traceback.format_exc().replace("\n", " | ")
#             print(f"[ERROR] {txt_path.name}: {e}\n{tb}")
#             yield f"data: [ERROR] {txt_path.name}: {str(e)}\n\n"

#     yield "data: [COMPLETE] All files processed.\n\n"
