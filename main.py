#RAG SERVER
from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import RAGPipeline  
from langchain_community.embeddings import HuggingFaceEmbeddings


# Initialize FastAPI app
app = FastAPI()

# Initialize RAG once (expensive)
rag = RAGPipeline()

# Request model
class QueryRequest(BaseModel):
    query: str

# Endpoint
@app.post("/query")
def query_rag(request: QueryRequest):
    response = rag.query(request.query)
    return {"answer": response}
