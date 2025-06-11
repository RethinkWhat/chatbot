from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

# Load your documents
loader = TextLoader("knowledge/sample.txt")  # change this to the actual files to be used
documents = loader.load()

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
