
from pdf2image import convert_from_path
from pdfminer.high_level import extract_text
import pytesseract
from scrapers.cleaner import Cleaner
import os, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class PDFScraper:
    def __init__(self, input_dir="knowledge/raw", output_dir="knowledge/txt"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def readPDF(self, file_path):
        try:
            text = extract_text(file_path)
            return text.strip() if text and len(text.strip()) > 0 else None
        except Exception as e:
            print(f"[Error] PDFMiner failed to read {file_path}: {e}")
            return None

    def readPDFImage(self, file):
        try:
            pages = convert_from_path(file, dpi=300)
            text = "".join(pytesseract.image_to_string(page) for page in pages)
        except Exception as e:
            print(f"[Error] OCR failed for {file} — {e}")
            return ""


    def scan_all_pdfs(self, use_ocr_fallback=True):
        txt_removed = 0
        for f in os.listdir(self.input_dir):
            if f.endswith(".txt"):
                try:
                    os.remove(os.path.join(self.input_dir, f))
                    txt_removed += 1
                except Exception as e:
                    logging.warning(f"[Cleanup] Could not remove {f}: {e}")
        if txt_removed:
            logging.info(f"[Cleanup] Removed {txt_removed} leftover .txt files.")

        found = False
        for filename in os.listdir(self.input_dir):
            if not filename.lower().endswith(".pdf"):
                continue
            found = True
            file_path = os.path.join(self.input_dir, filename)
            base_name = Path(filename).stem
            output_path = os.path.join(self.output_dir, base_name + ".txt")

            if os.path.exists(output_path):
                logging.info(f"[Skip] Already exists: {output_path}")
                continue

            logging.info(f"[PDF] Processing: {filename}")
            text = self.readPDF(file_path)

            if (not text or len(text) < 50) and use_ocr_fallback:
                logging.warning(f"[Fallback OCR] {filename} appears unreadable — using OCR")
                text = self.readPDFImage(file_path)

            if text and len(text.strip()) > 0:
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(text)
                logging.info(f"[Saved] → {output_path}")
            else:
                logging.error(f"[Failed] No extractable text from: {filename}")

        if not found:
            logging.warning(f"[PDF Scanner] No PDF files found in {self.input_dir}")

if __name__ == "__main__":
    scraper = PDFScraper()
    scraper.scan_all_pdfs()
