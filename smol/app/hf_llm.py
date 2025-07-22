import json, re, traceback, time
start = time.time()
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
#for parallel
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime
logging.basicConfig(
    level=logging.DEBUG,  # set to INFO if you want less noise
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)


# Check GPU
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")

# === Paths ===
RAW_TXT_DIR = Path("/app/knowledge/raw")
JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# === Load model ===
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_NAME = "HuggingFaceTB/SmolLM3-3B"

print(f"[INIT] Loading model '{MODEL_NAME}' on {DEVICE}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE)
print("[INIT] Model loaded.")

# === Text Cleaning ===
def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def filter_relevant_lines(text: str) -> str:
    lines = text.split("\n")
    return "\n\n".join(
        line for line in (l.strip() for l in lines)
        if line and (len(line) > 50 or line.endswith("?"))
    )

def preprocess_text(text: str) -> str:
    return filter_relevant_lines(clean_text(text))

def split_text_into_chunks(text, tokenizer, chunk_token_limit=1024):
    tokens = tokenizer.tokenize(text)
    chunks = [
        tokenizer.convert_tokens_to_string(tokens[i:i+chunk_token_limit])
        for i in range(0, len(tokens), chunk_token_limit)
    ]
    return chunks


# === JSON Extraction ===
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
    print("[WARNING] Unbalanced braces. Returning partial JSON.")
    return text[start:]

# === Call LLM ===
def get_json_from_text(chunk: str) -> dict:
    prompt = (
        "You are a JSON generator. ONLY return a valid JSON object. "
        "Do not include any explanation or formatting.\n\n"
        "Input text:\n" + chunk
    )

    messages = [{"role": "user", "content": prompt}]
    formatted_prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    inputs = tokenizer([formatted_prompt], return_tensors="pt").to(DEVICE)
    max_tokens = min(2048, 2048 - inputs["input_ids"].shape[-1])

    start = time.time()
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        temperature=0.2,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )
    print(f"[TIME] Generation took {time.time() - start:.2f} seconds")

    generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True)
    response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

    print(f"[DEBUG] Partial LLM output:\n{response[:300]}...\n")

    return json.loads(extract_first_json_block(response))


# === Stream inference per file ===
def parallel_jsonify(chunks, max_workers=4, base_name=""):
    results = []
    errors = []

    def process_chunk(index, chunk):
        start_time = datetime.now()
        logging.info(f"[START] Chunk #{index+1}/{len(chunks)} for '{base_name}'")

        short_chunk = chunk[:80].replace("\n", " ")
        logging.debug(f"         Text: {short_chunk}...")

        result = get_json_from_text(chunk)

        duration = (datetime.now() - start_time).total_seconds()
        logging.info(f"[DONE]  Chunk #{index+1} completed in {duration:.2f} sec")
        return (index, result)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(process_chunk, i, chunk): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                index, result = future.result()
                results.append(result)
            except Exception as e:
                logging.error(f"[ERROR] Chunk #{i+1}: {e}")
                errors.append((i, str(e)))

    return results, errors

def sequential_jsonify(chunks):
    results = []
    errors = []

    for i, chunk in enumerate(chunks):
        try:
            result = get_json_from_text(chunk)
            results.append(result)
        except Exception as e:
            errors.append((i, str(e)))

    return results, errors

def jsonify_stream():
    txt_files = list(RAW_TXT_DIR.glob("*.txt"))
    if not txt_files:
        yield "data: No .txt files found.\n\n"
        return

    yield f"data: Found {len(txt_files)} file(s).\n\n"

    for txt_path in txt_files:
        base_name = txt_path.stem
        try:
            print(f"[Processing] {txt_path.name}")
            raw_text = txt_path.read_text(encoding="utf-8").strip()

            if not raw_text or len(raw_text) < 50:
                yield f"data: [SKIP] {txt_path.name} is empty or too short.\n\n"
                continue

            preprocessed = preprocess_text(raw_text)
            if len(preprocessed) < 100:
                yield f"data: [SKIP] {txt_path.name} contains no usable content.\n\n"
                continue

            chunks = split_text_into_chunks(preprocessed, tokenizer)
            yield f"data: [START] {txt_path.name} split into {len(chunks)} chunk(s)...\n\n"

            try:
                results, errors = parallel_jsonify(chunks, max_workers=4, base_name=base_name)
                method = "Parallel"
            except Exception as e:
                print(f"[WARN] Parallel JSONify failed: {e}. Falling back to sequential.")
                results, errors = sequential_jsonify(chunks)
                method = "Sequential fallback"

            for i in range(len(results)):
                yield f"data: [Chunk {i+1}] ✓ ({method})\n\n"
            for i, err in errors:
                yield f"data: [Chunk {i+1}] ERROR: {err}\n\n"

            # Save all collected results
            json_path = JSON_OUTPUT_DIR / f"{base_name}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            yield f"data: [DONE] Saved {json_path.name} ({len(results)} chunks)\n\n"
            if errors:
                yield f"data: [WARNING] {len(errors)} chunks failed.\n\n"

        except Exception as e:
            tb = traceback.format_exc().replace("\n", " | ")
            yield f"data: [ERROR] {txt_path.name}: {str(e)}\n\n"
            print(f"[ERROR] {txt_path.name}: {e}\n{tb}")

    yield "data: [COMPLETE] All files processed.\n\n"




#======================
#        PHI
# import json, re, time
# from pathlib import Path
# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch

# RAW_TXT_DIR = Path("/app/knowledge/raw")
# JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
# JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# # Model setup: Phi-2 (non-chat model)
# MODEL_NAME = "microsoft/phi-2"
# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cpu")


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
#     raise ValueError("Unbalanced JSON.")


# def get_json_from_text(text: str) -> dict:
#     instruction = (
#         "Convert the following raw academic text into structured JSON. "
#         "Return **only valid JSON** without any commentary or formatting:\n\n"
#         + text[:4000]
#     )

#     if getattr(tokenizer, "chat_template", None):
#         # Use chat template if available (e.g., SmolLM3)
#         messages = [{"role": "user", "content": instruction}]
#         prompt = tokenizer.apply_chat_template(
#             messages, tokenize=False, add_generation_prompt=True
#         )
#     else:
#         # Manual formatting for non-chat models like phi-2
#         prompt = f"[INSTRUCTION] {instruction}"

#     inputs = tokenizer(prompt, return_tensors="pt").to("cpu")
#     outputs = model.generate(
#         **inputs,
#         max_new_tokens=2048,
#         temperature=0.2,
#         do_sample=False,
#         pad_token_id=tokenizer.eos_token_id
#     )

#     generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
#     response = tokenizer.decode(generated_ids, skip_special_tokens=True)
#     response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

#     return json.loads(extract_first_json_block(response))


# def jsonify_stream():
#     txt_files = list(RAW_TXT_DIR.glob("*.txt"))
#     if not txt_files:
#         yield "data: No .txt files found.\n\n"
#         return

#     yield f"data: Found {len(txt_files)} file(s).\n\n"

#     for txt_path in txt_files:
#         json_path = JSON_OUTPUT_DIR / (txt_path.stem + ".json")
#         try:
#             raw_text = txt_path.read_text(encoding="utf-8").strip()
#             if not raw_text:
#                 yield f"data: [SKIP] {txt_path.name} is empty.\n\n"
#                 continue

#             yield f"data: [START] Processing {txt_path.name}...\n\n"
#             json_data = get_json_from_text(raw_text)

#             with open(json_path, "w", encoding="utf-8") as f:
#                 json.dump(json_data, f, indent=2, ensure_ascii=False)

#             yield f"data: [DONE] Saved {json_path.name}\n\n"

#         except Exception as e:
#             error_msg = str(e).replace("\n", " ")
#             yield f"data: [ERROR] {txt_path.name}: {error_msg}\n\n"

#     yield "data: [COMPLETE] All files processed.\n\n"
