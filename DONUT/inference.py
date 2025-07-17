# inference.py
import os
import json
from PIL import Image
from pathlib import Path
from pdf2image import convert_from_path
from transformers import DonutProcessor, VisionEncoderDecoderModel, pipeline
import torch
import pytesseract

FINETUNED_MODELS_ROOT = Path("/app/donut-finetuned")
MAX_LENGTH = 1536
DPI = 200

# # Load online Hugging Face LLM pipeline
# print("[INFO] Initializing Hugging Face LLM pipeline (smolLM3-6b)...")
# llm_pipeline = pipeline("text-generation", model="HuggingFaceTB/smolLM3-6b")


def classify_document_type(filename):
    lower_name = filename.lower()
    if "calendar" in lower_name:
        return "calendar"
    elif "announcement" in lower_name or "memo" in lower_name:
        return "announcements"
    elif "catalog" in lower_name or "program" in lower_name:
        return "program_catalog"
    elif "school-prospectus" in lower_name or "organization" in lower_name:
        return "school_info"
    else:
        return "generic"


def load_model_for_type(doc_type):
    model_path = FINETUNED_MODELS_ROOT / doc_type
    if not model_path.exists():
        print(f"❌ No trained model for document type: {doc_type}")
        return None, None
    try:
        processor = DonutProcessor.from_pretrained(model_path)
        model = VisionEncoderDecoderModel.from_pretrained(model_path, ignore_mismatched_sizes=True)
        model.eval()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        return processor, model
    except Exception as e:
        print(f"❌ Failed to load model for {doc_type}: {e}")
        return None, None


def pdf_to_images(pdf_path):
    pages = convert_from_path(str(pdf_path), dpi=DPI)
    if not pages:
        raise ValueError(f"No pages found in PDF: {pdf_path}")
    widths, heights = zip(*(page.size for page in pages))
    total_height = sum(heights)
    max_width = max(widths)

    stitched_image = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))
    y_offset = 0
    for page in pages:
        stitched_image.paste(page, (0, y_offset))
        y_offset += page.height
    return stitched_image


def run_inference_on_pdf(pdf_path, output_json_path):
    doc_type = classify_document_type(pdf_path.name)
    processor, model = load_model_for_type(doc_type)
    if processor is None or model is None:
        print("❌ Inference skipped. Model not loaded.")
        return

    images = pdf_to_images(pdf_path)
    results = []

    print(f"[INFO] Processing {os.path.basename(pdf_path)} using model '{doc_type}'")
    pixel_values = processor(images=images, return_tensors="pt").pixel_values.to(model.device)
    task_prompt = f"<s_docvqa><s_question>Convert the document into structured JSON format for {doc_type} document</s_question><s_answer>"
    print(f"[DEBUG] Prompt: {task_prompt}")

    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(model.device)
    print(f"[DEBUG] Decoder input tokens: {processor.tokenizer.convert_ids_to_tokens(decoder_input_ids[0])}")

    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=MAX_LENGTH,
            early_stopping=True,
            repetition_penalty=1.5,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            bad_words_ids=[[processor.tokenizer.unk_token_id]]
        )

    result = processor.tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"[RAW OUTPUT] {result}")

    try:
        parsed = json.loads(result)
        results.append(parsed)
    except json.JSONDecodeError:
        # print("[WARNING] Invalid JSON. Triggering OCR and online LLM fallback.")
        # ocr_text = pytesseract.image_to_string(images)
        # print(f"[OCR TEXT] {ocr_text.strip()[:1000]}\n[...truncated]")

        # prompt = f"Convert the following text into structured JSON format :\n\n{ocr_text[:3000]}"
        # llm_response = llm_pipeline(prompt, max_new_tokens=1024)[0]['generated_text']
        # print(f"[LLM OUTPUT] {llm_response[:1000]}\n[...truncated]")

        # try:
        #     llm_json = json.loads(llm_response)
        #     results.append(llm_json)
        # except json.JSONDecodeError:
            #results.append({"error": "Invalid JSON from LLM", "raw_output": llm_response})
        results.append({"error": "Invalid JSON from LLM", "raw_output": results})
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DONE] Saved to {output_json_path}")


def run_inference_batch(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    processed_files = []

    for pdf_file in Path(input_dir).glob("*.pdf"):
        output_path = Path(output_dir) / (pdf_file.stem + ".json")
        run_inference_on_pdf(pdf_file, output_path)
        processed_files.append(pdf_file.name)

    return processed_files
