import os
from PIL import Image
from pytesseract import pytesseract

# Set paths
path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
images_folder = "images"
output_folder = "knowledge"
output_file = os.path.join(output_folder, "extractedImageTexts.txt")

# Set tesseract command path
pytesseract.tesseract_cmd = path_to_tesseract

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Initialize an empty string to hold all extracted text
all_text = ""

# Supported image extensions
valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

# Loop through all image files in the images folder
for filename in os.listdir(images_folder):
    if filename.lower().endswith(valid_extensions):
        image_path = os.path.join(images_folder, filename)
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            all_text += f"\n--- Text from {filename} ---\n{text.strip()}\n"
        except Exception as e:
            print(f"Error processing {filename}: {e}")

# Write the combined text to the output file
with open(output_file, "w", encoding="utf-8") as f:
    f.write(all_text)

print(f"Text extracted from images and saved to {output_file}")