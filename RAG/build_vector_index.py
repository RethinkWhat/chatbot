from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

from scrapers.web_scraper import run_scraper
#from scrapers.pdf_scraper import scan_all_pdfs
from scrapers.image_scraper import scan_images

from rag_pipeline import RAGPipeline

import os

RAW_DIR = "knowledge/txt"
CLEAN_DIR = "knowledge/cleaned"

class BuildVectorIndex:
    def run(self):

        #skip scraping for now
        #=================================================
        # run_scraper(urls_path="urls.txt", output_dir=DIR, depth=2)
        # print("Web scraping done.")
   
        # scan_all_pdfs()
        # print("PDF scanning done.")

        # scan_images(folder=DIR)
        #=================================================
        
        # 4. Load all .txt files and build vector index
        loader = DirectoryLoader(
            CLEAN_DIR,
            glob="**/*.txt",
            loader_cls=lambda path: TextLoader(path, encoding="utf-8")
        )
        documents = loader.load()

        if not documents:
            raise ValueError("No documents found. Please check the directory and file format.")

        #1000 & 200
        splitter = RecursiveCharacterTextSplitter(    
            separators=["\n\n", "\n", ".", " "],  # favors logical breaks
            chunk_size=512,
            chunk_overlap=50
        )
        
        chunks = splitter.split_documents(documents)

        embedding_model= HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
        vector_store = FAISS.from_documents(chunks, embedding_model)
        vector_store.save_local("vector_index")

        print("Vector index built and saved to 'vector_index/'")

if __name__ == "__main__":
    builder = BuildVectorIndex()
    builder.run()
    def __init__(self):
        os.makedirs(RAW_DIR, exist_ok=True)
        os.makedirs(CLEAN_DIR, exist_ok=True)
        self.rag = RAGPipeline()

    def run_scraping(self, run_web=True, run_pdf=True, run_img=True):
        if run_web:
            run_scraper(urls_path="urls.txt", output_dir=RAW_DIR, depth=2)
            print("✅ Web scraping completed.")
        if run_pdf:
            #scan_all_pdfs()
            print("✅ PDF scanning completed.")
        if run_img:
            scan_images(folder=RAW_DIR)
            print("✅ Image scanning completed.")

    def run_cleaning(self):
        count = 0
        for filename in os.listdir(RAW_DIR):
            if filename.endswith(".txt"):
                raw_path = os.path.join(RAW_DIR, filename)
                with open(raw_path, "r", encoding="utf-8") as f:
                    raw = f.read()
                cleaned = self.rag.paraphrase_with_ollama(raw, filename)
                clean_path = os.path.join(CLEAN_DIR, filename)
                with open(clean_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                count += 1
        print(f"✅ Cleaned {count} files with Ollama.")
        return count

    def build_index(self):
            os.makedirs(RAW_DIR, exist_ok=True)
            os.makedirs(CLEAN_DIR, exist_ok=True)

            # If cleaned directory is empty but raw files exist, clean them first
            cleaned_files = [f for f in os.listdir(CLEAN_DIR) if f.endswith(".txt")]
            raw_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".txt")]

            if not cleaned_files and raw_files:
                print("No cleaned data found. Cleaning raw .txt files...")

                # Reuse the same initialized pipeline
                rag = RAGPipeline()

                for filename in raw_files:
                    raw_path = os.path.join(RAW_DIR, filename)
                    with open(raw_path, "r", encoding="utf-8") as f:
                        raw = f.read()

                    cleaned = rag.paraphrase_with_ollama(raw, filename)

                    # Validate cleaned content before writing
                    if cleaned.strip():
                        clean_path = os.path.join(CLEAN_DIR, filename)
                        with open(clean_path, "w", encoding="utf-8") as f:
                            f.write(cleaned)
                        print(f"✅ Cleaned: {filename}")
                    else:
                        print(f"⚠️ Skipped (empty output): {filename}")

                print("✅ Cleaning complete.")


            # Build vector index from cleaned folder
            print("🔍 Building vector index from:", CLEAN_DIR)
            loader = DirectoryLoader(
                CLEAN_DIR,
                glob="**/*.txt",
                loader_cls=lambda path: TextLoader(path, encoding="utf-8")
            )
            documents = loader.load()

            if not documents:
                raise ValueError("No documents found in 'knowledge/cleaned/'. Please check input.")

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = splitter.split_documents(documents)

            embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vector_store = FAISS.from_documents(chunks, embedding_model)
            vector_store.save_local("vector_index")

            print("✅ Vector index built and saved to 'vector_index/'")
            return len(chunks)
