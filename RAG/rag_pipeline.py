from langchain_huggingface.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
import os
from langchain_community.chat_models import ChatOllama
from langchain_mistralai import ChatMistralAI
# Christian: JUN 19 =============
# adding imports for different LLMs
from langchain_community.chat_models import ChatOllama
from langchain_mistralai import ChatMistralAI
# ===============================

class RAGPipeline:
    def __init__(self,llm_backend: str = "ollama"):
        self.embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    def __init__(self,llm_backend: str = "ollama"):
        self.embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = FAISS.load_local(
            "vector_index",
            self.embedding,
            allow_dangerous_deserialization=True
        )
        self.retriever = self.vector_store.as_retriever()
        
        # choice for one of the LLMs
        if llm_backend.lower() == "mistral":
            print("Using MistralAI as LLM")
            llm = ChatMistralAI(
                api_key=os.getenv("MISTRAL_API_KEY") or "6UcG5oBmAwgGSW7fESb8gfZZgCEitFXJ",
                model="mistral-small"
            )
        elif llm_backend.lower() == "ollama":
            print("Using Ollama (llama3) as LLM")
            try:
                llm = ChatOllama(model="llama3")
            except Exception as e:
                raise RuntimeError("Ollama is not running. Please start with 'ollama serve'") from e
            
        else:
            raise ValueError(f"Unsupported LLM backend: {llm_backend}")
        
        # Christian: JUN 18 =============
        # choice for one of the LLMs
        if llm_backend.lower() == "mistral":
            print("Using MistralAI as LLM")
            llm = ChatMistralAI(
                api_key=os.getenv("MISTRAL_API_KEY") or "6UcG5oBmAwgGSW7fESb8gfZZgCEitFXJ",
                model="mistral-small"
            )
        elif llm_backend.lower() == "ollama":
            print("Using Ollama (llama3) as LLM")
            try:
                llm = ChatOllama(model="llama3")
            except Exception as e:
                raise RuntimeError("Ollama is not running. Please start with 'ollama serve'") from e
            
        else:
            raise ValueError(f"Unsupported LLM backend: {llm_backend}")

        self.qa_chain = RetrievalQA.from_chain_type(
            llm=ChatMistralAI(
                api_key='WTtgTOjSF3mxJsi2uxDhalwMl7uz2HZI',#os.getenv("MISTRAL_API_KEY"),
                model="mistral-small"  # or mistral-medium / mistral-large
            ),
            llm=llm,
            retriever=self.retriever
        )
        #================================

    def query(self, question: str) -> str:
        return self.qa_chain.invoke(question)