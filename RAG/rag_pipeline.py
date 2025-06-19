from langchain_huggingface.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
import os

class RAGPipeline:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = FAISS.load_local(
            "vector_index",
            self.embedding,
            allow_dangerous_deserialization=True
        )
        self.retriever = self.vector_store.as_retriever()

        self.qa_chain = RetrievalQA.from_chain_type(
            llm=ChatMistralAI(
                api_key='WTtgTOjSF3mxJsi2uxDhalwMl7uz2HZI',#os.getenv("MISTRAL_API_KEY"),
                model="mistral-small"  # or mistral-medium / mistral-large
            ),
            retriever=self.retriever
        )

    def query(self, question: str) -> str:
        return self.qa_chain.invoke(question)
        # TO ADD CONTEXT from FAISS