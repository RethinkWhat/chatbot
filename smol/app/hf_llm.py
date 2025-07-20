import json, re, time, traceback
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

RAW_TXT_DIR = Path("/app/knowledge/raw")
JSON_OUTPUT_DIR = Path("/app/knowledge/testJson")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load SMOL
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


def get_json_from_text(text: str) -> dict:
    prompt = (
        "You are a JSON generator. Convert the following raw text into structured JSON file.\n\n"
        "ONLY return valid JSON.\n\nInput text:\n" + text[:2000]
    )

    # Format as chat for SmolLM3
    messages = [{"role": "user", "content": prompt}]
    formatted_prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    inputs = tokenizer([formatted_prompt], return_tensors="pt").to("cpu")

    # Dynamically adjust max tokens based on input
    max_tokens = min(1024, 2048 - inputs["input_ids"].shape[-1])

    try:
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.2,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )

        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True)
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

        return json.loads(extract_first_json_block(response))

    except Exception as e:
        print(f"[GEN ERROR] Exception during generation: {e}")
        raise


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
            raw_text = txt_path.read_text(encoding="utf-8").strip()
            if not raw_text:
                yield f"data: [SKIP] {txt_path.name} is empty.\n\n"
                continue

            yield f"data: [START] Processing {txt_path.name}...\n\n"

            json_data = get_json_from_text(raw_text)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            yield f"data: [DONE] Saved {json_path.name}\n\n"

        except Exception as e:
            tb = traceback.format_exc().replace("\n", " | ")
            print(f"[ERROR] {txt_path.name}: {e}\n{tb}")
            yield f"data: [ERROR] {txt_path.name}: {str(e)}\n\n"

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
