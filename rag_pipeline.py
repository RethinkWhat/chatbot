from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.llms import OpenAI

class RAGPipeline:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = FAISS.load_local(
            "vector_index",
            self.embedding,
            allow_dangerous_deserialization=True
        )
        self.retriever = self.vector_store.as_retriever()
        self.qa_chain = RetrievalQA.from_chain_type(llm=OpenAI(), retriever=self.retriever)

    def query(self, question: str) -> str:
        return self.qa_chain.run(question)