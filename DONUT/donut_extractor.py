from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import DonutProcessor, VisionEncoderDecoderModel
from pdf2image import convert_from_path
from PIL import Image
import torch, json, os, gc
from pathlib import Path
import logging

os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SAFE_MAX_LENGTH = 512

# Create necessary folders
os.makedirs("knowledge/raw", exist_ok=True)
os.makedirs("knowledge/testJson", exist_ok=True)

class LayoutLMv3Extractor:
    def __init__(self):
        logger.info("⏳ Loading DonutProcessor and VisionEncoderDecoderModel...")
        self.processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        self.model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        logger.info("✅ Donut model loaded.")

    def extract(self, pdf_path: str) -> dict:
        logger.info(f"📄 Starting extraction for: {pdf_path}")
        images = convert_from_path(pdf_path, dpi=150)
        results = {}

        for page_num, image in enumerate(images, start=1):
            logger.info(f"🖼️ Processing page {page_num}")
            logger.debug(f"Page {page_num} image size: {image.size}, mode: {image.mode}")
            try:
                # Process image into pixel values
                pixel_values = self.processor(image, return_tensors="pt").pixel_values.to(self.device)

                # Use task-specific prompt
                task_prompt = "<s_docvqa><s_question>Summarize the document content in JSON format that Python can read.</s_question><s_answer>"
                decoder_input_ids = self.processor.tokenizer(
                        task_prompt, add_special_tokens=True, return_tensors="pt"
                    ).input_ids.to(self.device)
                # Generate output (simplified, safe params)
                output_ids = self.model.generate(
                    pixel_values,
                    decoder_input_ids=decoder_input_ids,
                    max_length=1024,
                    num_beams=1,
                    early_stopping=True,
                    use_cache=True,
                    do_sample=False,
                    pad_token_id=self.processor.tokenizer.pad_token_id
                )

                output = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0].strip()
                print("Generated token IDs:", output_ids.tolist())


                logger.debug(f"🧠 Output (raw) for page {page_num}: {output}")
                try:
                    results[f"page_{page_num}"] = json.loads(output)
                except Exception as e:
                    results[f"page_{page_num}"] = {
                        "raw_output": output,
                        "error": f"JSON decode failed: {e}"
                    }

            except Exception as e:
                logger.error(f"❌ Failed to process page {page_num}: {e}")
                results[f"page_{page_num}"] = {"error": f"Failed to process page {page_num}: {e}"}

        return results
