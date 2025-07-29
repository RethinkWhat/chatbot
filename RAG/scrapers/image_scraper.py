import os
import logging
from PIL import Image
from pathlib import Path
import pytesseract

# Optional: Set path to tesseract executable if not in PATH
# pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def scan_images(input_folder="knowledge/raw", output_folder="knowledge/txt"):
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

    scanned_count = 0
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(valid_extensions):
            image_path = os.path.join(input_folder, filename)
            txt_filename = Path(filename).stem + ".txt"
            txt_path = os.path.join(output_folder, txt_filename)

            try:
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img, lang="eng+fil").strip()

                if text:
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    logging.info(f"[Success] Extracted from {filename} → Saved to {txt_path}")
                    scanned_count += 1
                else:
                    if os.path.exists(txt_path):
                        os.remove(txt_path)
                    logging.info(f"[Info] No text found in {filename}. Skipped.")
            except Exception as e:
                logging.error(f"[Error] Failed to process {filename}: {e}")

    if scanned_count == 0:
        logging.warning("[Done] No images produced usable text.")
    else:
        logging.info(f"[Done] {scanned_count} images processed successfully.")

# Standalone execution
if __name__ == "__main__":
    scan_images()
