from transformers import pipeline
import json

print("[INFO] Loading SmolLM3-3B from Hugging Face...")
generator = pipeline("text-generation", model="HuggingFaceTB/SmolLM3-3B")

def get_json_from_text(text: str):
    prompt = f"Convert the following text into structured JSON format:\n\n{text[:3000]}"
    result = generator(prompt, max_new_tokens=2048)[0]['generated_text']

    try:
        return json.loads(result)
    except Exception:
        return {"error": "Invalid JSON", "raw_output": result}
