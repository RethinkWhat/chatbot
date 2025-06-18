from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import os

from langchain_community.document_loaders import DirectoryLoader
from scrapers.pdf_scraper import PDFScraper
import glob
import os

DIR = "KNOWLEDGE"
class BuildVectorIndex: 
    pdfScraper = PDFScraper()
    def run(self): 

        pdf_files = glob.glob(os.path.join(DIR, "**/*.pdf"), recursive=True)

        for pdf in pdf_files:
            content = self.pdfScraper.readPDF(pdf)
            if not content:
                self.pdfScraper.readPDFImage(pdf)
                
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
