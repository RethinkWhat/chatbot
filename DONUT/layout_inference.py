# layoutlmv3_infer.py
import os
from pathlib import Path
import json
from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification
from PIL import Image
import torch

# -------------------------------
# Configuration
# -------------------------------
MODEL_DIR = Path("/app/layoutlmv3-finetuned/program_catalog")
PDF_IMAGE_DIR = Path("/app/datasets/image/program_catalog")
OUTPUT_DIR = Path("/app/inference_output")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# -------------------------------
# Load model and processor
# -------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
processor = LayoutLMv3Processor.from_pretrained(MODEL_DIR)
model = LayoutLMv3ForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(device)
model.eval()

# -------------------------------
# Inference
# -------------------------------
def run_inference():
    for image_file in PDF_IMAGE_DIR.glob("*.png"):
        image = Image.open(image_file).convert("RGB")

        inputs = processor(image, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            prediction = torch.argmax(outputs.logits, dim=1).item()

        result = {
            "file": image_file.name,
            "prediction": prediction
        }

        output_path = OUTPUT_DIR / f"{image_file.stem}.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        print(f"✅ Inference complete for {image_file.name}: predicted class {prediction}")

if __name__ == "__main__":
    run_inference()
