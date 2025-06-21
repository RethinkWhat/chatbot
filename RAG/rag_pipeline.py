from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_mistralai import ChatMistralAI
import os

llmModel = None  # Initialize llmModel to be used later in the class

class RAGPipeline:
    def __init__(self, llm_backend: str = "ollama"):
        # Load embeddings and vector store
        self.embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = FAISS.load_local(
            "vector_index",
            self.embedding,
            allow_dangerous_deserialization=True
        )
        self.retriever = self.vector_store.as_retriever()
        print(self.retriever.get_relevant_documents("english teacher"))
        

        # Select LLM backend
        if llm_backend == "mistral":
            print("✅ Using MistralAI as LLM")
            self.llmModel = ChatMistralAI(
                api_key=os.getenv("MISTRAL_API_KEY") or "your-fallback-key",
                model="mistral-small"
            )

            # Build QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llmModel,
                retriever=self.retriever,
                chain_type="stuff"
            )
            # We do not build the chain here, since it is used for synchronous streaming
            # The Ollama chain will be made custom so that it streams word by word 
        elif llm_backend == "ollama":
            print("✅ Using Ollama (llama3) as LLM")
            try:
                self.llmModel = ChatOllama(
                    model="llama3", 
                    base_url="http://ollama:11434",
                    streaming=True  # Enable streaming
                    )
            except Exception as e:
                raise RuntimeError("Ollama is not running. Please start it with `ollama run llama3`") from e
        else:
            raise ValueError(f"❌ Unsupported LLM backend: {llm_backend}")


    # If Mistral is used, this method will return the answer to the question
    def query(self, question: str) -> str:
        return self.qa_chain.run(question)
    
    # If Ollama is used, this method will stream the answer to the question
    def get_ollama_stream(self, question: str):
        docs = self.retriever.get_relevant_documents(question)
        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = f"Use the context below to answer the question.\n\nContext: {context}\n\nQuestion: {question}"

        for chunk in self.llmModel.stream(prompt):
            yield chunk.content