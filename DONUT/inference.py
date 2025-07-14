# inference.py
import os
import json
from PIL import Image
from pathlib import Path
from pdf2image import convert_from_path
from transformers import DonutProcessor, VisionEncoderDecoderModel

import torch

MODEL_DIR = "/app/donut-finetuned"
processor = DonutProcessor.from_pretrained(MODEL_DIR)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_DIR, ignore_mismatched_sizes=True)
model.eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

def pdf_to_images(pdf_path):
    return convert_from_path(pdf_path, dpi=150)

def run_inference_on_pdf(pdf_path, output_json_path):
    images = pdf_to_images(pdf_path)
    results = []

    for i, img in enumerate(images):
        print(f"[INFO] Processing page {i+1} of {os.path.basename(pdf_path)}")
        pixel_values = processor(images=img, return_tensors="pt").pixel_values.to(device)
        task_prompt = "<s_docvqa><s_question>extract information</s_question><s_answer>"
        decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(device)

        with torch.no_grad():
            outputs = model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=1024,
                early_stopping=True,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                bad_words_ids=[[processor.tokenizer.unk_token_id]]
            )

        result = processor.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"[RAW OUTPUT] {result}")
        try:
            parsed = json.loads(result)
            results.append(parsed)
        except json.JSONDecodeError:
            results.append({"error": "Invalid JSON", "raw_output": result})

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DONE] Saved to {output_json_path}")

def run_inference_batch(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    processed_files = []

    for pdf_file in Path(input_dir).glob("*.pdf"):
        output_path = Path(output_dir) / (pdf_file.stem + ".json")
        run_inference_on_pdf(pdf_file, output_path)
        processed_files.append(pdf_file.name)

    return processed_files
