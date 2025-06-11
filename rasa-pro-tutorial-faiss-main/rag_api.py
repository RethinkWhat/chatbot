import threading
import time
from flask import Flask, request, jsonify, render_template_string
from typing import List, Union
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from ollama import chat
from llama_index.core.base.llms.types import ChatMessage, LLMMetadata
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.prompts import PromptTemplate

# Globals
llm_ready = False
query_engine = None

# LLM class
class OllamaLLM:
    def __init__(self, model="mistral"):
        self.model = model

    def complete(self, prompt: Union[str, object], **kwargs):
        prompt = self._ensure_string(prompt)
        print(f"[DEBUG] Final prompt sent to Ollama:\n{prompt}\n")
        response = chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]


    def predict(self, prompt: Union[str, object], **kwargs):
        return self.complete(prompt, **kwargs)

    def chat(self, messages: List[ChatMessage], **kwargs):
        full_prompt = "\n".join([m.content for m in messages])
        return self.complete(full_prompt, **kwargs)

    def _ensure_string(self, prompt):
        if isinstance(prompt, str):
            return prompt
        elif hasattr(prompt, "__str__"):
            return str(prompt)
        else:
            raise TypeError("Prompt must be a string or convertible to a string.")

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            is_chat_model=True,
            model_name=self.model,
            context_window=4096,
            num_output=512,
        )

# Settings config
Settings.llm = OllamaLLM()
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# Flask setup
app = Flask(__name__)
form_template = """
<!doctype html>
<title>Ask a Question</title>
<h2>Ask a question</h2>
<form method="post" action="/rag-query">
  <input type="text" name="question" style="width:300px">
  <input type="submit" value="Ask">
</form>
{% if answer %}
  <h3>Answer:</h3>
  <p>{{ answer }}</p>
{% endif %}
"""

@app.before_request
def warm_up_llm():
    global llm_ready, query_engine
    print("[RAG API] Warming up LLM and loading data...")
    try:
        documents = SimpleDirectoryReader("data").load_data()
        index = VectorStoreIndex.from_documents(documents)
        qa_prompt = PromptTemplate(
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Given the context above, answer the following question:\n"
            "Q: {query_str}\n"
            "A:"
        )
        query_engine = index.as_query_engine(text_qa_template=qa_prompt)
        # Pre-query to warm LLM
        query_engine.query("Hello")  # Dummy query to warm cache
        llm_ready = True
        print("[RAG API] Warm-up complete.")
    except Exception as e:
        print(f"[RAG API] Warm-up failed: {e}")
        llm_ready = False

# Threaded safe query with timeout (starts only *after* warm-up)
def safe_query(question, timeout=25):
    result = {}

    def task():
        try:
            result["response"] = query_engine.query(question)
        except Exception as e:
            result["error"] = str(e)

    thread = threading.Thread(target=task)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return None, "Query timed out internally"
    return result.get("response"), result.get("error")

@app.route("/", methods=["GET"])
def home():
    return "RAG API is live. Visit /rag-query to ask questions."

@app.route("/rag-query", methods=["GET", "POST"])
def rag_query():
    if not llm_ready:
        return jsonify({"answer": "LLM is still loading. Please try again shortly."}), 503

    if request.method == "POST":
        start_time = time.time()
        question = request.form.get("question") or request.json.get("question")
        print(f"[RAG API] Received question: {question}")

        response, error = safe_query(question, timeout=25)
        duration = time.time() - start_time
        print(f"[RAG API] Responded in {duration:.2f} seconds")

        if error:
            return jsonify({"answer": f"Error: {error}"}), 500
        return jsonify({"answer": str(response)})
    else:
        return render_template_string(form_template, answer=None)

if __name__ == "__main__":
    app.run(port=5001)
