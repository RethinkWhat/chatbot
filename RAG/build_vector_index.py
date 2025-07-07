from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

from scrapers.web_scraper import run_scraper
from scrapers.pdf_scraper import scan_all_pdfs
from scrapers.image_scraper import scan_images

import os
from rag_pipeline import RAGPipeline

RAW_DIR = "knowledge/txt"
CLEAN_DIR = "knowledge/cleaned"

class BuildVectorIndex:
    def __init__(self):
        os.makedirs(RAW_DIR, exist_ok=True)
        os.makedirs(CLEAN_DIR, exist_ok=True)

    def run_scraping(self, run_web=True, run_pdf=True, run_img=True):
        if run_web:
            run_scraper(urls_path="urls.txt", output_dir=RAW_DIR, depth=2)
            print("✅ Web scraping completed.")
        if run_pdf:
            scan_all_pdfs()
            print("✅ PDF scanning completed.")
        if run_img:
            scan_images(folder=RAW_DIR)
            print("✅ Image scanning completed.")

    def run_cleaning(self):
        from rag_pipeline import RAGPipeline  # Import here to avoid early vector load
        rag = RAGPipeline()
        count = 0
        for filename in os.listdir(RAW_DIR):
            if filename.endswith(".txt"):
                raw_path = os.path.join(RAW_DIR, filename)
                with open(raw_path, "r", encoding="utf-8") as f:
                    raw = f.read()
                cleaned = rag.paraphrase_with_ollama(raw, filename)
                clean_path = os.path.join(CLEAN_DIR, filename)
                with open(clean_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                count += 1
        print(f"✅ Cleaned {count} files with Ollama.")
        return count

    def build_index(self):
        os.makedirs(RAW_DIR, exist_ok=True)
        os.makedirs(CLEAN_DIR, exist_ok=True)

        cleaned_files = [f for f in os.listdir(CLEAN_DIR) if f.endswith(".txt")]
        raw_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".txt")]

        # Step 1: If no cleaned data but raw exists, clean it
        if not cleaned_files and raw_files:
            print("🧹 No cleaned data found. Cleaning raw .txt files...")
            rag = RAGPipeline()
            for filename in raw_files:
                raw_path = os.path.join(RAW_DIR, filename)
                with open(raw_path, "r", encoding="utf-8") as f:
                    raw = f.read()

                cleaned = rag.paraphrase_with_ollama(raw, filename)
                if cleaned.strip():
                    clean_path = os.path.join(CLEAN_DIR, filename)
                    with open(clean_path, "w", encoding="utf-8") as f:
                        f.write(cleaned)
                    print(f"✅ Cleaned: {filename}")
                else:
                    print(f"⚠️ Skipped empty cleaned file: {filename}")
            print("✅ Cleaning complete.")

        # Step 2: Build vector index
        cleaned_files = [f for f in os.listdir(CLEAN_DIR) if f.endswith(".txt")]
        if not cleaned_files:
            print("⚠️ No .txt files found in knowledge/cleaned/. Cannot build vector index.")
            return 0

        print("🔍 Building vector index from:", CLEAN_DIR)
        loader = DirectoryLoader(
            CLEAN_DIR,
            glob="**/*.txt",
            loader_cls=lambda path: TextLoader(path, encoding="utf-8")
        )
        documents = loader.load()

        if not documents:
            raise ValueError("❌ No documents loaded from 'knowledge/cleaned/'. Check directory structure.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)

        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_documents(chunks, embedding_model)
        vector_store.save_local("vector_index")

        print(f"✅ Vector index built from {len(chunks)} chunks and saved to 'vector_index/'")
        return len(chunks)
