from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.document_loaders import DirectoryLoader
from scrapers.pdf_scraper import PDFScraper
import glob
import os

#message box asking whether or not user wants to scrape the web, pdfs, and images
import tkinter as tk
from tkinter import messagebox

#calling scrapers into this pipeline
from scrapers.web_scraper import run_scraper 
from scrapers.pdf_scraper import scan_all_pdfs
from scrapers.image_scraper import scan_images

DIR = "knowledge"  # Directory where text files are stored

def ask_user(title, question):
    root = tk.Tk()
    root.withdraw()
    answer = messagebox.askyesno(title, question)
    root.destroy()
    return answer

class BuildVectorIndex:
    def run(self):
        # 1. Ask for web scraping
        if ask_user("Web Scraping Confirmation", "Do you want to run web scraping before scanning PDFs and images?"):
            run_scraper(urls_path="urls.txt", output_dir=DIR, depth=2)
        else:
            print("[Skip] Web scraping skipped.")

        # 2. Ask for PDF scanning
        if ask_user("PDF Scanning Confirmation", "Do you want to scan PDFs in the knowledge folder?"):
            scan_all_pdfs()
        else:
            print("[Skip] PDF scanning skipped.")

        # 3. Always run image scanning
        scan_images(folder=DIR)

        # 4. Load all .txt files and build vector index
        loader = DirectoryLoader(
            DIR,
            glob="**/*.txt",
            loader_cls=lambda path: TextLoader(path, encoding="utf-8")
        )
        documents = loader.load()

        if not documents:
            raise ValueError("No documents found. Please check the directory and file format.")

        splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        chunks = splitter.split_documents(documents)

        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_documents(chunks, embedding_model)
        vector_store.save_local("vector_index")

        print("Vector index built and saved to 'vector_index/'")

if __name__ == "__main__":
    builder = BuildVectorIndex()
    builder.run()