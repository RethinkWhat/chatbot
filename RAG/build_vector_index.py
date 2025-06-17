from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

# Single File
# Load your documents
#loader = TextLoader("knowledge/sample.txt")  # change this to the actual files to be used
#documents = loader.load()

# Multiple Files
from langchain_community.document_loaders import DirectoryLoader

class BuildVectorIndex: 
    def run(self): 
        # Load all text files from a directory
        loader = DirectoryLoader(
            "knowledge",  # change this to the directory containing your text files
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
