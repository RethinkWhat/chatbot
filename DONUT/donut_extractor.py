# donut_extractor.py

from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
import json
import os
from pdf2image import convert_from_path


class LayoutLMv3Extractor:
    def __init__(self):
        print("⏳ Loading DonutProcessor and VisionEncoderDecoderModel...")
        self.processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        self.model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        print("✅ Donut model loaded.")

    def extract(self, pdf_path: str) -> dict:
        # Convert all pages to images
        images = convert_from_path(pdf_path, dpi=200)
        results = {}

        for page_num, image in enumerate(images, start=1):
            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.to(self.device)
            task_prompt = "<s_docvqa><s_question>extract information</s_question><s_answer>"
            decoder_input_ids = self.processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(self.device)

            output_ids = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=1024,
                early_stopping=True,
                pad_token_id=self.processor.tokenizer.pad_token_id
            )

            output = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
            try:
                results[f"page_{page_num}"] = json.loads(output)
            except Exception as e:
                results[f"page_{page_num}"] = {"raw_output": output, "error": str(e)}

        return results
