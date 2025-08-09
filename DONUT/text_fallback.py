import os
import json
import requests
from pathlib import Path

# Example using Hugging Face Inference API
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/your-model-name"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
}

def txt_to_json(text, schema_hint="program_catalog"):
    prompt = f"""
Extract structured JSON from the following {schema_hint} document content.
Only return valid JSON without explanations.

Content:
\"\"\"
{text}
\"\"\"
JSON:
"""

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 1024},
    }

    response = requests.post(HUGGINGFACE_API_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        try:
            output = response.json()[0]['generated_text']
            start = output.find("{")
            end = output.rfind("}") + 1
            return json.loads(output[start:end])
        except Exception as e:
            print(f"⚠️ JSON parsing error: {e}")
            return None
    else:
        print(f"❌ HF API error: {response.status_code}")
        return None

def batch_convert_txt_to_json(txt_dir, out_dir, schema_hint="program_catalog"):
    txt_dir = Path(txt_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for txt_file in txt_dir.glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()

        json_obj = txt_to_json(content, schema_hint=schema_hint)
        if json_obj:
            out_path = out_dir / (txt_file.stem + ".json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(json_obj, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved: {out_path.name}")
        else:
            print(f"⚠️ Skipped: {txt_file.name}")
