import sys, json
from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image

processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")

def run(img_path):
    image = Image.open(img_path).convert("RGB")
    task_prompt = "<s_docvqa><s_question>Extract all info in JSON</s_question><s_answer>"
    pixel_values = processor(image, return_tensors="pt").pixel_values
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
    outputs = model.generate(pixel_values, decoder_input_ids=decoder_input_ids, max_length=2048)
    result = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    print(result)

if __name__ == "__main__":
    run(sys.argv[1])  # takes image path
