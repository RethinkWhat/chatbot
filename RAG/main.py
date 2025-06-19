#RAG SERVER
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_community.embeddings import HuggingFaceEmbeddings
import os # used to get user choice of LLM saved in device environment variable

# local Imports
from rag_pipeline import RAGPipeline  
from build_vector_index import BuildVectorIndex


# Build Knowledge. Can comment out this section if knowledge already built
build_vector_index = BuildVectorIndex()
build_vector_index.run()


# Initialize FastAPI app
app = FastAPI()

# Christian-JUN19====
# now user can choose between LLMs
llm_backend = os.getenv("LLM_BACKEND", "ollama") 
# Initialize RAG pipeline: now RAGPipelines has one argument llm_backend
rag_pipeline = RAGPipeline(llm_backend=llm_backend)


@app.get('/')
def read_root():
    return {"message": "Welcome to the RAG API. Use the /query endpoint to ask questions."}    

# Endpoint
@app.post("/query")
async def query(request: Request):
    body = await request.json()
    print("Received body:", body)  # Optional: Debug

    # Extract query from tracker
    query = body.get("query", "")

    if not query:
        return JSONResponse(
            status_code=200,
            content={"responses": [{"query": "No query found in message."}], "events": []}
        )

    # 👇 RAG PIPELINE IMPLE
    response = rag_pipeline.query(query)
    print(response)
    response = JSONResponse(
        status_code=200,
        content={"response" : response.get("result", "no answer found.")} 
        )
    print(response)

    return response