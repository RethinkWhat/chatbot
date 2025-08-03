import json, re, time, traceback
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from datetime import datetime
import torch.nn as nn
if not hasattr(nn, "RMSNorm"):
    from transformers.models.llama.modeling_llama import LlamaRMSNorm
    nn.RMSNorm = LlamaRMSNorm

RAW_TXT_DIR = Path("/app/knowledge/txt")
JSON_OUTPUT_DIR = Path("/app/knowledge/Json")
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load SMOL
MODEL_NAME = "HuggingFaceTB/SmolLM3-3B"
# Detect device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(device)

print(f"Model loaded on {device}")


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

# Clean output from LLM before parsing
def clean_llm_output(output: str) -> str:
    output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)
    output = output.strip()

    # Remove markdown block wrappers
    if output.startswith("```") and "{" in output:
        output = output[output.find("{"):]  # cut off everything before first {
    output = re.sub(r"```.*", "", output, flags=re.DOTALL).strip()
    return output

# Preprocess raw txt

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

# JSONification

def get_json_from_text(text: str) -> dict:
    prompt = (
        "You are a JSON generator. Convert the following raw text into structured JSON file.\n\n"
        "ONLY return valid JSON.\n\nInput text:\n" + text
    )

    use_extended_thinking = False
    messages = []
    if not use_extended_thinking:
        messages.append({"role": "system", "content": "/no_think"})
    else:
        messages.append({"role": "system", "content": "/think"})
    messages.append({"role": "user", "content": prompt})

    formatted_prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    inputs = tokenizer([formatted_prompt], return_tensors="pt").to(device)
    max_tokens = min(2048, 4000 - inputs["input_ids"].shape[-1])

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
        cleaned_response = clean_llm_output(response)

        try:
            json_str = extract_first_json_block(cleaned_response)
            return json.loads(json_str)
        except Exception as e:
            print(f"[PARSE ERROR] Could not extract valid JSON from LLM response.")
            print(f"[RAW OUTPUT]\n{cleaned_response}")
            raise ValueError("Failed to parse JSON from model output.") from e

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
        try:
            print(f"[Processing] {txt_path.name}")
            raw_text = txt_path.read_text(encoding="utf-8").strip()
            if not raw_text:
                yield f"data: [SKIP] {txt_path.name} is empty.\n\n"
                continue

            yield f"data: [START] Processing {txt_path.name}...\n\n"

            json_data = get_json_from_text(raw_text)

            # === Inject metadata ===
            date_str = datetime.today().strftime("%Y-%m-%d")
            if isinstance(json_data, dict):
                json_data.setdefault("metadata", {})["date_created"] = date_str
            else:
                json_data = {
                    "content": json_data,
                    "metadata": {
                        "date_created": date_str
                    }
                }

            # === Save JSON with date in filename ===
            base_name = txt_path.stem
            json_filename = f"{base_name}_{date_str}.json"
            json_path = JSON_OUTPUT_DIR / json_filename

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            yield f"data: [DONE] Saved {json_filename}\n\n"

        except Exception as e:
            tb = traceback.format_exc().replace("\n", " | ")
            print(f"[ERROR] {txt_path.name}: {e}\n{tb}")
            yield f"data: [ERROR] {txt_path.name}: {str(e)}\n\n"

    yield "data: [COMPLETE] All files processed.\n\n"

