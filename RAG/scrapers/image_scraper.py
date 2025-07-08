import os
from PIL import Image
from pytesseract import pytesseract
from pathlib import Path

# Set paths
path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
images_folder = "images"
output_folder = "knowledge"
output_file = os.path.join(output_folder, "extractedImageTexts.txt")

def scan_images(input_folder="knowledge/raw", output_folder="knowledge/txt"):
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(valid_extensions):
            image_path = os.path.join(input_folder, filename)
            txt_filename = Path(filename).stem + ".txt"
            txt_path = os.path.join(output_folder, txt_filename)

            try:
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img).strip()

                if text:
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"[Success] Extracted from {filename} → Saved to {txt_path}")
                else:
                    if os.path.exists(txt_path):
                        os.remove(txt_path)
                    print(f"[Info] No text found in {filename}. Skipping save.")

            except Exception as e:
                print(f"[Error] Failed to process {filename}: {e}")

# standalone running
if __name__ == "__main__":
    scan_images()