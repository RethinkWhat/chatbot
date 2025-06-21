from PyPDF2 import PdfReader
import os
from pdf2image import convert_from_path
import pytesseract
from scrapers.cleaner import Cleaner
import os
from pathlib import Path

DIR = "knowledge"
# There are two types of PDF scrapers initalized under this class
class PDFScraper: 
    # Reads a regular PDF file
    def readPDF(self, file):
        reader = PdfReader(file)  
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
        if not text.strip():
            return None  # Return None if there's no text
        
        # Clean the extracted text
        with open(os.path.join(DIR, Path(file).stem) +".txt", "w", encoding="utf-8") as f:
            f.write(text)
        return text
    
    #Reads flattened PDFs / PDFs with images
    def readPDFImage(self, file):
        pages = convert_from_path(file, dpi=300)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page)

        # Clean the extracted text
        cleaned_text = Cleaner.runOCRCleaner(text)

        with open(os.path.join(DIR, Path(file).stem) +".txt", "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        return cleaned_text

def scan_all_pdfs():
    scraper = PDFScraper()
    for filename in os.listdir(DIR):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(DIR, filename)
            print(f"[PDF Scanner] Scanning: {filename}")
            text = scraper.readPDF(file_path)
            if text is None or len(text.strip()) < 50:
                print(f"[Fallback OCR] {filename} appears flattened — using OCR")
                scraper.readPDFImage(file_path)
            else:
                print(f"[Success] Extracted text from: {filename}")
                
if __name__ == "__main__":
    scan_all_pdfs()
