from sklearn import base
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.output_parsers import StrOutputParser
from pathlib import Path
import torch
import uuid
import posthog
import requests, json, time, os, re, subprocess


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
        # client = weaviate.connect_to_custom(
        #     http_host="weaviate",         # your Docker service name or localhost
        #     http_port=8080,
        #     http_secure=False,
        #     grpc_host="weaviate",         # same as http_host if gRPC isn't separately routed
        #     grpc_port=50051,
        #     grpc_secure=False
        # )
        # questions = client.collections.create(
        #     name="NaviBot",
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

        # navibot = client.collections.get("NaviBot")
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
        #         questions = client.collections.get("NaviBot")  # You can increase the limit as needed
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
    
    #new sol: JSONify pdf 
    def jsonify_pdf_with_layoutlm(self, pdf_path: str) -> dict:
        processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base", revision="main")
        model = LayoutLMv3ForQuestionAnswering.from_pretrained("microsoft/layoutlmv3-base")

        pages = convert_from_path(pdf_path, dpi=300)
        if not pages:
            return {"error": "No pages found in PDF"}

        results = []
        for i, image in enumerate(pages):
            encoding = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**encoding)
            # NOTE: LayoutLMv3 by default is for QA tasks; needs fine-tuning or zero-shot formatting
            # Here we just simulate a placeholder structure
            results.append({
                "page": i + 1,
                "raw_text": pytesseract.image_to_string(image, lang="eng+fil").strip()
            })

        return {"document": Path(pdf_path).name, "pages": results}
    
    def jsonifyTxt(self, raw_text_or_path: str, is_pdf_path=False) -> dict:
        """
        If `is_pdf_path` is True, treat `raw_text_or_path` as a PDF file path to extract via LayoutLMv3.
        Else, fallback to legacy LLM JSONification (if needed).
        """
        try:
            if is_pdf_path:
                outputs = self.layoutlm.extract_from_pdf(raw_text_or_path)
                # Optionally post-process outputs here if needed
                return {
                    "source": os.path.basename(raw_text_or_path),
                    "layoutlmv3_output": outputs
                }
            else:
                raise NotImplementedError("Legacy LLM-based extraction is disabled. Use PDF path with LayoutLMv3.")
        except Exception as e:
            return {"error": str(e)}
    # def jsonifyTxt(self, text: str) -> dict:
    #     """
    #     Clean the input text and use LLM to convert it to structured JSON output.
    #     """
    #     cleaned_text = self._clean_text_for_jsonification(raw_text)
        

    #     system_prompt = (
    #         "You are a document-to-JSON converter.\n"
    #         "You must extract structured information from the document and return only a valid JSON object.\n"
    #         "Make sure to retain full names (even if split across lines) and roles like Dean, Professor, Justice, etc.\n"
    #         "Do NOT drop prefixes like 'DR.', 'PROF.', 'CA JUSTICE', or 'ATTY.'.\n"
    #         "Do NOT include explanations, formatting hints, or markdown.\n"
    #         "Do NOT wrap the output in triple backticks or say 'Here is the JSON'.\n"
    #         "Avoid returning empty arrays or fields unless they are clearly needed.\n"
    #         "Preserve factual details, and group items logically.\n"
    #         "Only return valid JSON parseable by `json.loads()` in Python.\n"
    #     )
    #     prompt = f"{system_prompt}\n\nDocument:\n{text.strip()}\n\nOutput a single well-formatted JSON."

    #     response = self.get_ollama_completion(instruction)
    #     cleaned = self.extract_json_block(response)

    #     # Try to extract valid JSON content
    #     try:
    #         parsed = json.loads(cleaned)
    #         return parsed
    #     except Exception as e:
    #         print("[ERROR] JSON decoding failed. Raw LLM output returned instead.")
    #         return {"raw_output": response, "error": str(e)}

#testing new jsonification method
    def jsonify_all_cleaned_txt(self):
        input_dir = "knowledge/cleaned"
        output_dir = "knowledge/testJson"
        os.makedirs(output_dir, exist_ok=True)

        for filename in os.listdir(input_dir):
            if not filename.endswith(".txt"):
                continue

            txt_path = os.path.join(input_dir, filename)
            json_path = os.path.join(output_dir, Path(filename).stem + ".json")

            if os.path.exists(json_path):
                print(f"[Skip] Already exists: {json_path}")
                continue

            with open(txt_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            print(f"[Processing] → {filename}")
            result = self.jsonifyTxt(raw_text)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"[✓] JSON saved → {json_path}")
            
    def extract_json_block(self, text: str) -> str:
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        match = re.search(r"({.*})", text, re.DOTALL)
        return match.group(1) if match else text.strip()

    def classify_document(self, text: str) -> str:
        upper = text.upper()

        keyword_sets = {
            "program_catalog": [
                "PROGRAM EDUCATIONAL OBJECTIVES", "PEO", "PLO",
                "LEARNING OUTCOMES", "CAREER PATHS", "PROGRAM OUTCOMES"
            ],
            "schedule": [
                "COURSE SCHEDULE", "UNITS", "LLM", "TIME", "DATE", "INSTRUCTOR", "PROFESSOR"
            ],
            "law_course": [
                "JUSTICE", "SUPREME COURT", "LEGAL THEORY", "JURISPRUDENCE", "LAW", "ATTY.", "CA JUSTICE"
            ],"acad_calendar": [
                "REGISTRATION", "EXAMS", "SEMESTER", "HOLY WEEK", "GRADUATION", "BREAK", "BACCALAUREATE", "FOUNDATION WEEK"
            ],
        }

        match_scores = {}
        for doc_type, keywords in keyword_sets.items():
            match_scores[doc_type] = sum(kw in upper for kw in keywords)

        # Pick the type with the most keyword matches
        best_match = max(match_scores, key=match_scores.get)
        if match_scores[best_match] > 1:  # Require at least 2 matches to be confident
            return best_match
        return "generic"



    def _clean_text_for_jsonification(self, text: str) -> str:
        # Remove control characters
        text = re.sub(r'[\x0c\u000c\f]+', '', text)
        text = re.sub(r'[\t\r]+', '', text)
        text = re.sub(r'[ \xa0]+', ' ', text)

        # Remove headings like 'S C H O O L  O F  A C C O U N T A N C Y'
        text = re.sub(r'\b(?:[A-Z] ?){4,}\b', '', text)

        # Fix hyphenation at line breaks
        text = re.sub(r'-\n', '', text)

        # Collapse multiple spaces and newlines
        text = re.sub(r'\n{2,}', '\n\n', text)
        text = re.sub(r'[ ]{2,}', ' ', text)
        text = re.sub(r'\s+\n', '\n', text)

        # Fix bullet lines (e.g., lines ending in ;) split by newlines
        lines = text.split('\n')
        fixed_lines = []
        buffer = ""

        for line in lines:
            if not line.strip():
                fixed_lines.append(buffer.strip())
                buffer = ""
                continue

            # If line ends with ; or , or incomplete sentence, assume it's a bullet
            if line.strip()[-1:] in (';', ',') or line.strip()[-1].islower():
                buffer += " " + line.strip()
            else:
                buffer += " " + line.strip()
                fixed_lines.append(buffer.strip())
                buffer = ""

        if buffer:
            fixed_lines.append(buffer.strip())

        return '\n'.join(fixed_lines).strip()


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
        
    def get_prompt_by_type(self, doc_type: str, cleaned_text: str) -> str:
        prompt_file = f"prompts/{doc_type}.txt"
        if not os.path.exists(prompt_file):
            prompt_file = "prompts/fallback_general.txt"

        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()

        return template.replace("{{CONTENT}}", cleaned_text.strip())
    
# JSONification using Donut
    def get_layoutlm_completion(image_path):
        try:
            result = subprocess.run(
                ["/venv-donut/bin/python", "donut_worker.py", image_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print("[ERROR] Donut subprocess failed:", e.stderr)
            return ""

    def jsonify_pdf_with_layoutlm(self, pdf_path: str) -> dict:
        from transformers import DonutProcessor, VisionEncoderDecoderModel
        from PIL import Image
        import pdf2image

        processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa", use_fast=False)
        model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")

        images = pdf2image.convert_from_path(pdf_path, dpi=200)
        if not images:
            return {"error": "No pages found in PDF"}

        image = images[0].convert("RGB")
        pixel_values = processor(image, return_tensors="pt").pixel_values
        task_prompt = "<s_docvqa><s_question>Extract all structured information in JSON</s_question><s_answer>"
        decoder_input_ids = processor.tokenizer(task_prompt, return_tensors="pt").input_ids

        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=1024,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id
        )

        decoded = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        try:
            return json.loads(decoded)
        except Exception as e:
            return {"raw_output": decoded, "error": str(e)}
