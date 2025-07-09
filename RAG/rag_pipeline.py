from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.output_parsers import StrOutputParser
import torch
import uuid
import posthog
import requests, json, time, os, re


import weaviate
from weaviate import WeaviateClient
from weaviate.classes.config import Configure
import time
import textwrap # for paraphrasing the knowledge base

from constants import apologyMsg



llmModel = None  # Initialize llmModel to be used later in the class


class RAGPipeline:
    def __init__(self, llm_backend: str = "ollama"):
        try:
            posthog.api_key = "phc_eZjTrWqsuZNwwsm6hURdjgrFeRMSdSD1Rjx8i3uHZFu" #"phx_hNGq3WucDTsZWAlzpj2WdJV2H5hFGbHroGnyuaQG7fGq25C" #os.environ["POSTHOG_API_KEY"]
            posthog.host = "https://app.posthog.com" #os.environ['POSTHOG_HOST'] 
        except KeyError:
            raise ValueError("Please set POSTHOG_API_KEY and POSTHOG_HOST environment variables")
        
        # comment out the section if it is already run once.
      #--------------------------------  START ------------------------------------------------------
        # client = weaviate.connect_to_custom(
        #     http_host="weaviate",         # your Docker service name or localhost
        #     http_port=8080,
        #     http_secure=False,
        #     grpc_host="weaviate",         # same as http_host if gRPC isn't separately routed
        #     grpc_port=50051,
        #     grpc_secure=False
        # )
        # questions = client.collections.create(
        #     name="NaviBot40",
        #     vectorizer_config=Configure.Vectorizer.text2vec_ollama(     # Configure the Ollama embedding integration
        #         api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
        #         model="nomic-embed-text",                               # The model to use
        #     ),
        #     generative_config=Configure.Generative.ollama(              # Configure the Ollama generative integration
        #         api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
        #         model="llama3.2",                                       # The model to use
        #     )
        # )
        # client.close()  # Free up resources

        # client = weaviate.connect_to_custom(
        #     http_host="weaviate",         # your Docker service name or localhost
        #     http_port=8080,
        #     http_secure=False,
        #     grpc_host="weaviate",         # same as http_host if gRPC isn't separately routed
        #     grpc_port=50051,
        #     grpc_secure=False
        # )

        # navibot = client.collections.get("NaviBot40")
        # # Step 4: Read and parse all JSON files
        # data = []
        # for filename in os.listdir("knowledge/json"):
        #     if filename.endswith(".json"):
        #         filepath = os.path.join("knowledge/json", filename)
        #         try:
        #             with open(filepath, "r", encoding="utf-8") as f:
        #                 json_data = json.load(f)

        #                 if isinstance(json_data, dict):
        #                     title = json_data.get("title", filename)
        #                     for key, value in json_data.items():
        #                         if key == "title":
        #                             continue  # Already stored as 'title'

        #                         # Skip empty content
        #                         if not value:
        #                             continue

        #                         chunk = {
        #                             "title": f"{title} - {key}".strip(),
        #                             "answer": json.dumps(value, indent=2),
        #                             "category": filename
        #                         }
        #                         data.append(chunk)
        #                 else:
        #                     print(f"Skipping {filename}: not a valid JSON object.")

        #         except json.JSONDecodeError as e:
        #             print(f"Failed to decode {filename}: {e}")

        # # Insert chunks in batches
        # with navibot.batch.fixed_size(batch_size=200) as batch:
        #     for item in data:
        #         batch.add_object({
        #             "title": item["title"][:300],
        #             "answer": item["answer"],
        #             "category": item["category"]
        #         })
        #         if batch.number_errors > 10:
        #             print("Batch import stopped due to excessive errors.")
        #             break

        #         failed_objects = navibot.batch.failed_objects
        #         if failed_objects:
        #             print(f"Number of failed imports: {len(failed_objects)}")
        #             print(f"First failed object: {failed_objects[0]}")

        #         # Fetch and print all objects
        #         questions = client.collections.get("NaviBot40")  # You can increase the limit as needed
        #         # Print nicely
        #         results = questions.query.fetch_objects(limit=100)

        #         # for obj in results.objects:
        #         #     print("UUID:", obj.uuid)
        #         #     print("Properties:", obj.properties)
        #         #     print("-" * 40)

        # client.close()  # Free up resources

        #--------------------------------  END ------------------------------------------------------

        try:
            # Select LLM backend
            print("Using Ollama (llama3) as LLM")
            self.llmModel = ChatOllama(
                model="llama3:8b", 
                base_url="http://ollama:11434",
                temperature=0.4,
                streaming=True  # Enable streaming
                )
            self.memory = ConversationBufferWindowMemory(k=2)
            self.chain = ConversationChain(
                llm=self.llmModel,
                memory=self.memory,
                verbose=True,
                input_key="input",     # This matches what the default prompt expects
                output_key="answer"
            )

            
            print("Connecting to Ollama at:", self.llmModel.base_url)
        except Exception as e:
                raise RuntimeError("Ollama is not running. Please start it with `ollama run llama3`") from e
        
        
    def task(self, distinct_id, input, output, event="llm-task", timestamp=None, session_id=None, properties=None):
        props = properties if properties else {}
        props["$llm_input"] = input
        props["$llm_output"] = output

        if session_id:
            props["$session_id"] = session_id

        posthog.capture(
            distinct_id=distinct_id, event=event, properties=props, timestamp=timestamp, disable_geoip=False
        )

    
    def predict(self, message: str, distinct_id: str, session_id: str, query: str) -> str:
        # 1. Call Rasa
        try:
            # 2. Extract Rasa response
            reply_text = self.get_ollama_stream(question=message)
        except Exception as e:
            print(f"Error calling Rasa: {e}")
            return "Sorry, I couldn't reach the assistant."

        # 3. Track in PostHog
        try:
            self.task(
                distinct_id=distinct_id,
                input=message,
                output=reply_text,
                session_id=session_id,
                properties={"source": "rasa-web-client"}
            )
        except Exception as e:
            print(f"PostHog tracking failed: {e}")

        return reply_text
    


    def get_ollama_stream(self, question: str):
        start = time.time()

        client = weaviate.connect_to_custom(
            http_host="weaviate",         # your Docker service name or localhost
            http_port=8080,
            http_secure=False,
            grpc_host="weaviate",         # same as http_host if gRPC isn't separately routed
            grpc_port=50051,
            grpc_secure=False
        )

        questions = client.collections.get("NaviBot")

        response = questions.query.near_text(
                    query=question,
                    limit=10,
                 #   distance=0.50,
                    return_metadata=["distance"]  
        )

        questions = client.collections.get("NaviBot")  # This should be the collection where you ingested the data


        client.close()
        print("response: ", response)


        context = "\n\n".join([
            f"{obj.properties['title'].split(' _ ')[-1]} - Document {i+1}:\n{obj.properties['answer']}  (Distance: {obj.metadata.distance:.4f}):"
            for i, obj in enumerate(response.objects)
        ])

        prompt = f"""
You are a helpful assistant. Use the documents below to answer the question.

QUESTION:
{question}

DOCUMENTS:
{context}

Only use the documents to answer. If the answer is not found, say {apologyMsg}
"""
        response = self.chain.predict(input=prompt)
        print("LLM RESPONSE: ", response )
        return response
    
    def jsonifyTxt(self, text: str) -> dict:
        system_prompt = (
            "You are a document-to-JSON converter.\n"
            "You will be given academic documents which may include poorly formatted or OCR-scanned text.\n"
            "Fix noisy artifacts like excessively spaced headings (e.g. 'C O M P U T I N G') and decode them properly.\n"
            "Group related information under logical JSON keys such as title, program, job_opportunities, contact_info, etc.\n"
            "Only return a valid, compact JSON object — do not include markdown, triple backticks, or extra explanations.\n"
            "Preserve all meaningful details. List items as arrays if applicable."
        )

        prompt = (
            f"{system_prompt}\n\n"
            f"Document:\n{text.strip()}\n\n"
            "Output JSON:"
        )

        raw_output = self.get_ollama_completion(prompt)
        clean_output = self.extract_json_block(raw_output)

        try:
            return json.loads(clean_output)
        except json.JSONDecodeError:
            print("[ERROR] JSON decoding failed. Raw LLM output returned instead.")
            return {"raw_output": raw_output}

    def extract_json_block(self, text: str) -> str:
        """Extract a valid JSON object from LLM response (cleaning markdown wrappers, etc.)."""
        # Prefer block inside triple-backtick markdown if present
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Otherwise, find first JSON-like block in the response
        match = re.search(r"({.*})", text, re.DOTALL)
        return match.group(1) if match else text
    def get_ollama_completion(self, prompt: str, retries: int = 3, delay: float = 2.0) -> str:
        if not self.llmModel:
            raise RuntimeError("LLM is not initialized.")

        try:
            llm = ChatOllama(
                model="llama3:8b",
                base_url="http://ollama:11434",
                temperature=0.4,
                streaming=False
            )
            response = llm.invoke(prompt)

            # Try multiple common formats safely
            if isinstance(response, str):
                return response.strip()

            if hasattr(response, "content"):
                return response.content.strip()

            if isinstance(response, dict) and "content" in response:
                return response["content"].strip()

            # Fallback: best guess
            return str(response).strip()

        except Exception as e:
            print(f"[ERROR] Failed to get Ollama completion: {e}")
            return ""
