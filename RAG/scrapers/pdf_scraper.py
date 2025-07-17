from pdf2image import convert_from_path
from pdfminer.high_level import extract_text
import pytesseract
from scrapers.cleaner import Cleaner
import os, logging
from pathlib import Path
import fitz  # PyMuPDF for per-page control

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class PDFScraper:
    def __init__(self, input_dir="knowledge/raw", output_dir="knowledge/raw", pages_per_chunk=5):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.pages_per_chunk = pages_per_chunk
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_page_text_chunks(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            chunks = []
            current_chunk = []

            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                ocr_text = ""

                # If there's little to no text, fallback to OCR
                if len(text) < 50:
                    logging.warning(f"[Page {i+1}] Not enough text, applying OCR")
                    images = convert_from_path(pdf_path, dpi=300, first_page=i+1, last_page=i+1)
                    for img in images:
                        ocr_text += pytesseract.image_to_string(img, lang="eng+fil")
                    ocr_text = Cleaner.runOCRCleaner(ocr_text.strip())
                else:
                    logging.info(f"[Page {i+1}] Text extracted via PDF")

                # Merge text + OCR if needed
                if text and ocr_text:
                    merged_text = f"{text}\n\n[OCR Supplement]\n{ocr_text}"
                else:
                    merged_text = text or ocr_text

                current_chunk.append(merged_text)

                # Every `pages_per_chunk` pages, store a chunk
                if (i + 1) % self.pages_per_chunk == 0 or (i + 1) == len(doc):
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []

            return chunks

        except Exception as e:
            logging.error(f"[Error] Failed to extract {pdf_path}: {e}")
            return []

    def extract_page_text(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            full_text = []
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if len(text) >= 50:
                    logging.info(f"[Page {i+1}] Text extracted via PDF")
                    full_text.append(text)
                else:
                    logging.warning(f"[Page {i+1}] Not enough text, applying OCR")
                    images = convert_from_path(pdf_path, dpi=300, first_page=i+1, last_page=i+1)
                    ocr_text = ""
                    for img in images:
                        ocr_text += pytesseract.image_to_string(img, lang="eng+fil")
                    full_text.append(Cleaner.runOCRCleaner(ocr_text.strip()))
            return "\n\n".join(full_text)
        except Exception as e:
            logging.error(f"[Error] Failed to extract {pdf_path}: {e}")
            return ""

    def scan_all_pdfs(self):
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

            logging.info(f"[PDF] Processing: {filename}")
            chunks = self.extract_page_text_chunks(file_path)

            if not chunks:
                logging.error(f"[Failed] No extractable text from: {filename}")
                continue

            for idx, chunk_text in enumerate(chunks, 1):
                chunk_filename = f"{base_name}-{idx}.txt"
                output_path = os.path.join(self.output_dir, chunk_filename)

                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(chunk_text)
                logging.info(f"[Saved] → {output_path}")

        if not found:
            logging.warning(f"[PDF Scanner] No PDF files found in {self.input_dir}")


if __name__ == "__main__":
    scraper = PDFScraper()
    scraper.scan_all_pdfs()
