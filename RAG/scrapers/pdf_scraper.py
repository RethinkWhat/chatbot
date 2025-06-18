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
            text += page.extract_text()

        # Clean the extracted text
        with open(os.path.join(DIR, Path(file).stem) +".txt", "w", encoding="utf-8") as f:
            f.write(text)
        return text
    
    #Reads a FLATTENED PDF file, which is a PDF that does not have text layers
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

