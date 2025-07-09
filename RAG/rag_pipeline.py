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
        
    #     comment out the section if it is already run once.
    #   --------------------------------  START ------------------------------------------------------
        client = weaviate.connect_to_custom(
            http_host="weaviate",         # your Docker service name or localhost
            http_port=8080,
            http_secure=False,
            grpc_host="weaviate",         # same as http_host if gRPC isn't separately routed
            grpc_port=50051,
            grpc_secure=False
        )
        questions = client.collections.create(
            name="NaviBot",
            vectorizer_config=Configure.Vectorizer.text2vec_ollama(     # Configure the Ollama embedding integration
                api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
                model="nomic-embed-text",                               # The model to use
            ),
            generative_config=Configure.Generative.ollama(              # Configure the Ollama generative integration
                api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
                model="llama3.2",                                       # The model to use
            )
        )
        client.close()  # Free up resources

        client = weaviate.connect_to_custom(
            http_host="weaviate",         # your Docker service name or localhost
            http_port=8080,
            http_secure=False,
            grpc_host="weaviate",         # same as http_host if gRPC isn't separately routed
            grpc_port=50051,
            grpc_secure=False
        )

        navibot = client.collections.get("NaviBot")
        # Step 4: Read and parse all JSON files
        data = []
        for filename in os.listdir("knowledge/json"):
            if filename.endswith(".json"):
                filepath = os.path.join("knowledge/json", filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                        if isinstance(json_data, dict):
                            title = json_data.get("title", filename)
                            for key, value in json_data.items():
                                if key == "title":
                                    continue  # Already stored as 'title'

                                # Skip empty content
                                if not value:
                                    continue

                                chunk = {
                                    "title": f"{title} - {key}".strip(),
                                    "answer": json.dumps(value, indent=2),
                                    "category": filename
                                }
                                data.append(chunk)
                        else:
                            print(f"Skipping {filename}: not a valid JSON object.")

                except json.JSONDecodeError as e:
                    print(f"Failed to decode {filename}: {e}")

        # Insert chunks in batches
        with navibot.batch.fixed_size(batch_size=200) as batch:
            for item in data:
                batch.add_object({
                    "title": item["title"][:300],
                    "answer": item["answer"],
                    "category": item["category"]
                })
                if batch.number_errors > 10:
                    print("Batch import stopped due to excessive errors.")
                    break

                failed_objects = navibot.batch.failed_objects
                if failed_objects:
                    print(f"Number of failed imports: {len(failed_objects)}")
                    print(f"First failed object: {failed_objects[0]}")

                # Fetch and print all objects
                questions = client.collections.get("NaviBot")  # You can increase the limit as needed
                # Print nicely
                results = questions.query.fetch_objects(limit=100)

                # for obj in results.objects:
                #     print("UUID:", obj.uuid)
                #     print("Properties:", obj.properties)
                #     print("-" * 40)

        client.close()  # Free up resources

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
            self.memory = ConversationBufferWindowMemory(k=0)
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
You are a helpful assistant. Use the information provided below to answer the user's question directly and concisely. 

- Do NOT say "Based on the documents" or "According to the text".
- Do NOT refer to any documents, sources, or context.
- Just answer as if you already know the information.
- If the answer is not found, say {apologyMsg}. Do not add extra information.

Information:
{context}

Question: {question}

Answer:

"""

        response = self.chain.predict(input=prompt)
        print("LLM RESPONSE: ", response )
        return response
    
    def jsonifyTxt(self, text: str) -> dict:
        """
        Clean the input text and use LLM to convert it to structured JSON output.
        """
        cleaned_text = self._clean_text_for_jsonification(raw_text)

        system_prompt = (
            "You are a document-to-JSON converter.\n"
            "You must extract structured information from the document and return only a valid JSON object.\n"
            "Make sure to retain full names (even if split across lines) and roles like Dean, Professor, Justice, etc.\n"
            "Do NOT drop prefixes like 'DR.', 'PROF.', 'CA JUSTICE', or 'ATTY.'.\n"
            "Do NOT include explanations, formatting hints, or markdown.\n"
            "Do NOT wrap the output in triple backticks or say 'Here is the JSON'.\n"
            "Avoid returning empty arrays or fields unless they are clearly needed.\n"
            "Preserve factual details, and group items logically.\n"
            "Only return valid JSON parseable by `json.loads()` in Python.\n"
        )
        prompt = f"{system_prompt}\n\nDocument:\n{text.strip()}\n\nOutput a single well-formatted JSON."

        response = self.get_ollama_completion(instruction)
        cleaned = self.extract_json_block(response)

        # Try to extract valid JSON content
        try:
            parsed = json.loads(cleaned)
            return parsed
        except Exception as e:
            print("[ERROR] JSON decoding failed. Raw LLM output returned instead.")
            return {"raw_output": response, "error": str(e)}

    def extract_json_block(self, text: str) -> str:
        """
        Try to extract a clean JSON block from a possibly messy LLM output.
        """
        # Remove triple backticks and preambles
        text = re.sub(r"```(?:json)?", "", text)
        text = re.sub(r"```", "", text)
        text = text.strip()

        # Try to locate a JSON object
        match = re.search(r"{[\s\S]*}", text)
        if match:
            return match.group(0)

        # Fallback: just return the full text
        return text



    def _clean_text_for_jsonification(self, text: str) -> str:
        text = re.sub(r'[\x0c\f]+', '', text)  # Remove form feeds
        text = re.sub(r'-\n', '', text)        # Join hyphenated breaks
        text = re.sub(r'\s+\n', '\n', text)    # Clean trailing whitespace
        text = re.sub(r'[^\S\r\n]{2,}', ' ', text)  # Collapse extra spaces
        text = re.sub(r'\n{2,}', '\n\n', text)      # Normalize spacing

        # Join numbered lists split on separate lines (e.g., "1.\n" to "1. ")
        text = re.sub(r'\n(\d+)\.\s*\n', r'\n\1. ', text)

        # Fix broken bullet-style lines without numbers
        text = re.sub(r'(?<=[a-zA-Z0-9,;])\n(?=[a-zA-Z])', ' ', text)

        # Remove fake spaced-out headings
        text = re.sub(r'\b(?:[A-Z] ?){3,}\b', '', text)

        return text.strip()


    def _clean_llm_json_output(self, output: str) -> str:
        output = re.sub(r"^```(?:json)?\\s*", "", output.strip(), flags=re.IGNORECASE)
        output = re.sub(r"\\s*```$", "", output.strip())
        output = re.sub(r"(?i)^here is.*json.*?:", "", output.strip())
        return output.strip()
    def get_ollama_completion(self, prompt: str) -> str:
        if not self.llmModel:
            raise RuntimeError("LLM is not initialized.")

        try:
            non_streaming_llm = ChatOllama(
                model="llama3:8b",
                base_url="http://ollama:11434",
                temperature=0.4,
                streaming=False  # Force non-streaming
            )
            response = non_streaming_llm.invoke(prompt)
            if isinstance(response, str):
                return response.strip()
            if hasattr(response, "content"):
                return response.content.strip()
            if isinstance(response, dict) and "content" in response:
                return response["content"].strip()
            return str(response).strip()
        except Exception as e:
            print(f"[ERROR] Failed to get Ollama completion: {e}")
            return ""
