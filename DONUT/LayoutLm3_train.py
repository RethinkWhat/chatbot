# layoutlmv3_train.py
import os
from pathlib import Path
from datasets import load_dataset, Dataset
from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification, TrainingArguments, Trainer
from PIL import Image
import json
import torch

# -------------------------------
# CONFIGURATION
# -------------------------------
PDF_DIR = Path("/app/datasets/types/program_catalog/pdfs")
LABEL_DIR = Path("/app/datasets/labels/program_catalog/labels")
OUTPUT_DIR = Path("/app/layoutlmv3-finetuned/program_catalog")
MODEL_NAME = "microsoft/layoutlmv3-base"

# -------------------------------
# Initialize processor and model
# -------------------------------
processor = LayoutLMv3Processor.from_pretrained(MODEL_NAME)
model = LayoutLMv3ForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)

# -------------------------------
# Data loading (mockup example)
# -------------------------------
def load_examples():
    data = []
    for label_file in LABEL_DIR.glob("*.json"):
        base = label_file.stem
        pdf_image_path = PDF_DIR / f"{base}.png"

        if not pdf_image_path.exists():
            print(f"⚠️ Missing image for {base}, skipping.")
            continue

        with open(label_file, "r", encoding="utf-8") as f:
            try:
                label = json.load(f)
            except:
                continue

        data.append({
            "image": str(pdf_image_path),
            "text": json.dumps(label)
        })

    return Dataset.from_list(data)

# -------------------------------
# Preprocessing function
# -------------------------------
def preprocess(example):
    image = Image.open(example["image"]).convert("RGB")
    encoding = processor(image, return_tensors="pt")
    encoding = {k: v.squeeze(0) for k, v in encoding.items()}
    encoding["labels"] = torch.tensor(1)  # Dummy label
    return encoding

# -------------------------------
# Main training
# -------------------------------
def main():
    dataset = load_examples()
    dataset = dataset.map(preprocess)
    dataset.set_format("torch")

    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=2,
        num_train_epochs=3,
        logging_dir=str(OUTPUT_DIR / "logs"),
        logging_steps=10,
        save_strategy="epoch",
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        tokenizer=processor,
    )

    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    processor.save_pretrained(OUTPUT_DIR)

if __name__ == "__main__":
    main()
