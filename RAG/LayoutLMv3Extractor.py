#libs for JSONification
from transformers import DonutProcessor,VisionEncoderDecoderModel
from pdf2image import convert_from_path
from PIL import Image
import torch
from layoutlm_extractor import LaymoutLMv3Extractor


class LayoutLMv3Extractor:
    def __init__(self):
        self.processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        self.model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def extract_from_pdf(self, pdf_path, max_pages=3):
        pages = convert_from_path(pdf_path, dpi=200)[:max_pages]
        outputs = []

        for i, page in enumerate(pages):
            page = page.convert("RGB")
            pixel_values = self.processor(images=page, return_tensors="pt").pixel_values.to(self.device)
            task_prompt = "<s_docvqa><s_question>Extract structured fields like schedule, programs, contacts, dates, etc.</s_question><s_answer>"
            decoder_input_ids = self.processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(self.device)

            output_ids = self.model.generate(pixel_values, decoder_input_ids=decoder_input_ids, max_length=1024)
            result = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
            outputs.append(result)

        return outputs