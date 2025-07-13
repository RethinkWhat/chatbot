import os, json
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image

# 🔧 Configuration
PDF_DIR = "datasets/pdfs"
LABEL_DIR = "datasets/labels"
IMG_OUT_DIR = "datasets/images"
OUTPUT_JSONL = "datasets/training.jsonl"

os.makedirs(IMG_OUT_DIR, exist_ok=True)
output = []

for pdf_path in Path(PDF_DIR).glob("*.pdf"):
    base_name = pdf_path.stem
    label_path = Path(LABEL_DIR) / f"{base_name}.json"

    if not label_path.exists():
        print(f"⚠️ No label for {base_name}, skipping.")
        continue

    # Load JSON label
    with open(label_path, "r", encoding="utf-8") as f:
        label_data = json.load(f)

    print(f"📄 Converting: {pdf_path.name}")
    pages = convert_from_path(str(pdf_path), dpi=150)

    for idx, page in enumerate(pages, start=1):
        image_filename = f"{base_name}-page-{idx}.png"
        image_path = Path(IMG_OUT_DIR) / image_filename
        page.save(image_path)

        output.append({
            "image_path": str(image_path),
            "ground_truth": label_data
        })

# 💾 Write final training.jsonl
with open(OUTPUT_JSONL, "w", encoding="utf-8") as out_f:
    for item in output:
        json.dump(item, out_f, ensure_ascii=False)
        out_f.write("\n")

print(f"✅ Done. {len(output)} samples written to {OUTPUT_JSONL}")
