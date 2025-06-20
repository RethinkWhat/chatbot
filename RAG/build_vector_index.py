from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import os

from langchain_community.document_loaders import DirectoryLoader
from scrapers.pdf_scraper import PDFScraper
import glob
import os

#calling scrapers into this pipeline
from scrapers.web_scraper import run_scraper 
from scrapers.pdf_scraper import scan_all_pdfs
from scrapers.image_scraper import scan_images


DIR = "knowledge"  # Directory where text files are stored
class BuildVectorIndex: 
    # Web Scraper 
    run_scraper(urls_path="urls.txt", output_dir=DIR, depth=2)
    
    # PDF scraper
    scan_all_pdfs()  # Scan all PDFs in the knowledge directory
    
    # pdfScraper = PDFScraper()
    # Image scraper 
    scan_images(folder=DIR, output_file=os.path.join(DIR, "extractedImageTexts.txt"))

    def run(self): 
        # pdf_files = glob.glob(os.path.join(DIR, "**/*.pdf"), recursive=True)

        # for pdf in pdf_files:
        #     content = self.pdfScraper.readPDF(pdf)
        #     if not content:
        #         self.pdfScraper.readPDFImages(pdf)
        
                
        # Load all text files from a directory
        loader = DirectoryLoader(
            DIR,  # directory containing text files
            glob="**/*.txt",  # load all .txt files recursively
            #loader_cls=TextLoader
            
            #Christian-JUN17: Use lambda to specify encoding
            loader_cls=lambda path: TextLoader(path, encoding="utf-8")
        )
        documents = loader.load()

        # Ensure documents are loaded
        if not documents:
            raise ValueError("No documents found. Please check the directory and file format.")

        # Split into chunks
        splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        chunks = splitter.split_documents(documents)

        # Use embeddings
        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Create vector store
        vector_store = FAISS.from_documents(chunks, embedding_model)

        # Save to local directory
        vector_store.save_local("vector_index")

        print("Vector index built and saved to 'vector_index/'")
