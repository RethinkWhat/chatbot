from PyPDF2 import PdfReader, errors
from pdf2image import convert_from_path
import pytesseract
from scrapers.cleaner import Cleaner
import os
from pathlib import Path

INPUT_DIR = "knowledge/raw"
OUTPUT_DIR = "knowledge/txt"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class PDFScraper:
    def readPDF(self, file):
        text = ""
        try:
            reader = PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
        except errors.PdfReadError as e:
            print(f"[Error] Cannot read {file} using PdfReader — {e}")
            return None

        return text if text.strip() else None

    def readPDFImage(self, file):
        try:
            pages = convert_from_path(file, dpi=300)
            text = "".join(pytesseract.image_to_string(page) for page in pages)
        except Exception as e:
            print(f"[Error] OCR failed for {file} — {e}")
            return ""

        return Cleaner.runOCRCleaner(text)

def scan_all_pdfs():
    scraper = PDFScraper()

    # Step 1: Clean up leftover .txt files in raw directory
    for f in os.listdir(INPUT_DIR):
        if f.endswith(".txt"):
            try:
                os.remove(os.path.join(INPUT_DIR, f))
                print(f"[Cleanup] Removed leftover TXT: {f}")
            except Exception as e:
                print(f"[Cleanup Error] Couldn't remove {f}: {e}")

    found = False
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            found = True
            file_path = os.path.join(INPUT_DIR, filename)
            base_name = Path(filename).stem
            output_path = os.path.join(OUTPUT_DIR, base_name + ".txt")

            print(f"[PDF Scanner] Scanning: {filename}")
            text = scraper.readPDF(file_path)

            if text is None or len(text.strip()) < 50:
                print(f"[Fallback OCR] {filename} appears flattened or unreadable — using OCR")
                text = scraper.readPDFImage(file_path)

            if text and len(text.strip()) > 0:
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(text)
                print(f"[Saved] Text written to: {output_path}")
            else:
                print(f"[Failed] Could not extract any text from: {filename}")

    if not found:
        print(f"[PDF Scanner] No PDF files found in {INPUT_DIR}")

if __name__ == "__main__":
    scan_all_pdfs()
