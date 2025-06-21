import os
from PIL import Image
from pytesseract import pytesseract
from pathlib import Path

# Set paths
path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
images_folder = "images"
output_folder = "knowledge"
output_file = os.path.join(output_folder, "extractedImageTexts.txt")

def scan_images(folder="knowledge"):
    os.makedirs(folder, exist_ok=True)
    valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

    for filename in os.listdir(folder):
        if filename.lower().endswith(valid_extensions):
            image_path = os.path.join(folder, filename)
            txt_filename = Path(filename).stem + ".txt"
            txt_path = os.path.join(folder, txt_filename)

            try:
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img)

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text.strip())

                print(f"[Success] Text from {filename} saved to {txt_filename}")
            except Exception as e:
                print(f"[Error] Failed to process {filename}: {e}")

# standalone running
if __name__ == "__main__":
    scan_images()