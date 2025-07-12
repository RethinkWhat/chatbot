from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import DonutProcessor, VisionEncoderDecoderModel
from pdf2image import convert_from_path
from PIL import Image
import torch, json, os, gc
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        # Convert all pages to images
        print(f"DEBUG: Converting PDF to images from {pdf_path}")
        images = convert_from_path(pdf_path, dpi=150) # You can still try lowering DPI if you face OOM later
        results = {}

        for page_num, image in enumerate(images, start=1):
            print(f"DEBUG: Processing page {page_num}/{len(images)}")
            print(f"DEBUG: Image size: {image.size}, mode: {image.mode}")
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.to(self.device)
            task_prompt = "<s_docvqa><s_question>extract information</s_question><s_answer>"

            # Explicitly add padding for the decoder input IDs
            decoder_input_ids = self.processor.tokenizer(
                task_prompt,
                add_special_tokens=False,
                return_tensors="pt",
                padding="max_length", # Pad to the model's max_length
                max_length=self.processor.tokenizer.model_max_length # Use the tokenizer's max length
            ).input_ids.to(self.device)
            print(f"DEBUG: Decoder pixel values shape {pixel_values.shape},dtype: {pixel_values.dtype}, device: {pixel_values.device}")
            print(f"DEBUG: Decoder input ids shaope {decoder_input_ids.shape}, dtype: {decoder_input_ids.dtype}, device: {decoder_input_ids.device}")
            output_ids = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=1024,
                min_length=1,
                num_beams=1,
                early_stopping=True,
                do_sample=False,
                pad_token_id=self.processor.tokenizer.pad_token_id,
                no_repeat_ngram_size=3,
                
            )

            output = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
            print(f"DEBUG: Raw model output for page {page_num}: {output}")
            try:
                results[f"page_{page_num}"] = json.loads(output)
            except Exception as e:
                results[f"page_{page_num}"] = {"raw_output": output, "error": str(e)}

        return results


# ✅ Now use the class
extractor = LayoutLMv3Extractor()

@app.get("/list-pdfs")
def list_pdfs():
    pdfs = [f for f in os.listdir("knowledge/raw") if f.lower().endswith(".pdf")]
    return {"files": pdfs}

@app.post("/trigger/jsonify-pdf/{filename}")
async def jsonify_pdf(filename: str):
    input_path = os.path.join("../knowledge/raw", filename)
    output_path = os.path.join("../knowledge/testJson", Path(filename).stem + ".json")

    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        result = extractor.extract(input_path)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return {"filename": filename, "json": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

