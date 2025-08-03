from langchain_ollama import ChatOllama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory

import json, time, os, re

import weaviate
from weaviate.classes.config import Configure
import time
import textwrap # for paraphrasing the knowledge base

from constants import apologyMsg
import re


llmModel = None  # Initialize llmModel to be used later in the class


class RAGPipeline:
    def __init__(self, llm_backend: str = "ollama"):

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
            name="navibot15",
            vectorizer_config=Configure.Vectorizer.text2vec_ollama(     # Configure the Ollama embedding integration
                api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
                model="nomic-embed-text",                               # The model to use
            ),
            generative_config=Configure.Generative.ollama(              # Configure the Ollama generative integration
                api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
                model="llama3:8b",                                       # The model to use
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

        navibot = client.collections.get("navibot15")
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
                questions = client.collections.get("navibot15")  # You can increase the limit as needed
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
            print("Using Ollama (LLAMA3:8b) as LLM")
            self.llmModel = ChatOllama(
                model="llama3:8b", 
                base_url="http://ollama:11434",
                temperature=0.2,
                streaming=True  # Enable streaming
                )
            self.memory = ConversationBufferWindowMemory(k=0) # Number of recent chats to include in convversation chain
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
    
    def predict(self, message: str, distinct_id: str, session_id: str, query: str) -> str:
        try:
            # 2. Extract Rasa response
            reply_text = self.get_ollama_stream(question=message)
        except Exception as e:
            print(f"Error calling Rasa: {e}")
            return "Sorry, I couldn't reach the assistant."

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

        questions = client.collections.get("navibot15")

        response = questions.query.near_text(
                    query=question,
                    limit=10,
                    distance=0.70,
                    return_metadata=["distance"]  
        )

        questions = client.collections.get("navibot15")  # This should be the collection where you ingested the data

        client.close()
        print("response: ", response)


        context = "\n\n".join([
            f"{obj.properties['title'].split(' _ ')[-1]} - {obj.properties['answer']} \n"
            for i, obj in enumerate(response.objects)
        ])

        print("THIS IS THE CONTEXT: ", context)
        if not re.search(r'[a-zA-Z]', context):
            return apologyMsg
        prompt = f"""
You are a helpful assistant designed to answer questions only for students based strictly on the provided documents.


- The current date is July 17, 2025.
- Only use information that is explicitly stated.
- Job opportunities, descriptions, or objectives are not equivalent to subjects or course listings.
- I expect you to answer on based off the information I give you.
- Don't apologize.
- Always provide all relevant details from the infomration provided in a clear and specific way. Provide a single detailed response.
- Do not say "According to the context", "Based on the provided documents", " is not explicitly stated in the given information," just simply provide an answer.
- NEVER say phrases like "the provided documents", "according to the context", or "based on the source". Just answer plainly. 
If the answer is not known, respond ONLY with "{apologyMsg}" Do NOT elaborate or mention the documents at all.
- When asked “Who is [person]?”, respond with their full name **and** any titles, roles, or affiliations mentioned in the documents. Do not omit available details.
- Collate all of the related information and give it to me. 
- Do not present similar abbreviations. Make sure it is an EXACT match.
- If asked "who" give me the name of the person with USEFUL information, otherwise respond with {apologyMsg}. If the information does not mention the person, respond with {apologyMsg}
---

{context}


QUESTION:  
{question}


Output format rule: Answers MUST NOT contain phrases referencing the source such as "documents", "context", or "provided materials".

ANSWER:
"""
        response = self.chain.predict(input=prompt)
        print("LLM RESPONSE: ", response )
        
        return response
