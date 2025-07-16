# train_donut.py
import os, json, traceback, logging
from pathlib import Path
from datasets import Dataset
from transformers import (
    DonutProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from PIL import Image
from pdf2image import convert_from_path
import torch

# -------------------------------
# Logging Setup
# -------------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# -------------------------------
# CONFIGURATION
# -------------------------------
MODEL_NAME = "naver-clova-ix/donut-base-finetuned-docvqa"
BASE_DATA_DIR = "./datasets"
OUTPUT_BASE_DIR = "./donut-finetuned"
MAX_TRAIN_SAMPLES = 50
NUM_EPOCHS = 3
MAX_LENGTH = 768
DPI = 100

processor = DonutProcessor.from_pretrained(MODEL_NAME)

# -------------------------------
# Utilities
# -------------------------------
def stitch_pdf_to_image(pdf_path):
    pages = convert_from_path(str(pdf_path), dpi=DPI)
    widths, heights = zip(*(page.size for page in pages))
    total_height = sum(heights)
    max_width = max(widths)

    stitched_image = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))
    y_offset = 0
    for page in pages:
        stitched_image.paste(page, (0, y_offset))
        y_offset += page.height
    return stitched_image

def classify_document_type(filename: str) -> str:
    lower_name = filename.lower()
    if "calendar" in lower_name:
        return "calendar"
    elif "announcement" in lower_name or "memo" in lower_name:
        return "announcement"
    elif "catalog" in lower_name or "program" in lower_name:
        return "program_catalog"
    else:
        return "generic"

# -------------------------------
# Data Loading
# -------------------------------
def load_training_examples(task_name: str, limit=None):
    logger.info(f"📚 Loading training examples for task: {task_name}...")
    pdf_dir = Path(BASE_DATA_DIR) / task_name / "pdfs"
    json_dir = Path(BASE_DATA_DIR) / task_name / "labels"
    data = []

    for json_file in json_dir.glob("*.json"):
        base = json_file.stem
        pdf_path = pdf_dir / f"{base}.pdf"
        if not pdf_path.exists():
            logger.warning(f"⚠️ PDF missing for {json_file.name}")
            continue

        try:
            stitched_img = stitch_pdf_to_image(pdf_path)
        except Exception as e:
            logger.warning(f"⚠️ Failed to process PDF {pdf_path.name}: {e}")
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                label = json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Invalid JSON in {json_file.name}: {e}")
            continue

        prompt = f"<s_docvqa><s_question>extract structured JSON for {task_name}</s_question><s_answer>"
        data.append({
            "image": stitched_img,
            "task_prompt": prompt,
            "ground_truth": json.dumps(label, ensure_ascii=False)
        })

        if limit and len(data) >= limit:
            break

    logger.info(f"✅ Loaded {len(data)} training samples.")
    return data

# -------------------------------
# Preprocessing
# -------------------------------
def preprocess_example(example):
    image = example["image"]
    if image.mode != "RGB":
        image = image.convert("RGB")

    pixel_values = processor.image_processor(image, return_tensors="pt").pixel_values.squeeze(0)
    text = example["task_prompt"] + example["ground_truth"]
    tokenized = processor.tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        max_length=MAX_LENGTH,
        truncation=True
    )
    labels = tokenized.input_ids.squeeze(0)
    labels[labels == processor.tokenizer.pad_token_id] = -100
    return {
        "pixel_values": pixel_values,
        "labels": labels
    }

# -------------------------------
# Collate Function
# -------------------------------
def collate_fn(batch):
    pixel_values = torch.stack([x["pixel_values"] for x in batch])
    labels = torch.nn.utils.rnn.pad_sequence(
        [x["labels"] for x in batch],
        batch_first=True,
        padding_value=processor.tokenizer.pad_token_id
    )
    return {"pixel_values": pixel_values, "labels": labels}

# -------------------------------
# Training
# -------------------------------
def train_donut_model(task_name: str):
    try:
        logger.info("⏳ Initializing model...")
        model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

        if "<s_docvqa>" not in processor.tokenizer.get_vocab():
            processor.tokenizer.add_special_tokens({"additional_special_tokens": ["<s_docvqa>"]})
            model.decoder.resize_token_embeddings(len(processor.tokenizer))

        from transformers.models.mbart.modeling_mbart import MBartLearnedPositionalEmbedding
        MAX_NEW_POSITION_EMBEDDINGS = 1536
        model.decoder.model.decoder.embed_positions = MBartLearnedPositionalEmbedding(
            MAX_NEW_POSITION_EMBEDDINGS + model.decoder.config.pad_token_id + 1,
            model.decoder.config.d_model
        )
        model.decoder.config.max_position_embeddings = MAX_NEW_POSITION_EMBEDDINGS
        model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids("<s_docvqa>")
        model.config.pad_token_id = processor.tokenizer.pad_token_id
        model.config.eos_token_id = processor.tokenizer.eos_token_id
        model.config.vocab_size = len(processor.tokenizer)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)

        samples = load_training_examples(task_name, limit=MAX_TRAIN_SAMPLES)
        if not samples:
            raise ValueError("❌ No training samples found.")

        dataset = Dataset.from_list(samples)
        dataset = dataset.map(preprocess_example, remove_columns=["image", "task_prompt", "ground_truth"])
        dataset.set_format("torch")

        output_dir = os.path.join(OUTPUT_BASE_DIR, task_name)
        os.makedirs(output_dir, exist_ok=True)

        args = Seq2SeqTrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=2,
            num_train_epochs=NUM_EPOCHS,
            learning_rate=3e-5,
            save_strategy="no",
            logging_dir="./logs",
            predict_with_generate=True,
            remove_unused_columns=False,
            fp16=torch.cuda.is_available(),
            logging_steps=10,
            save_total_limit=2,
            warmup_steps=max(1, len(dataset) // 4),
            weight_decay=0.01
        )

        trainer = Seq2SeqTrainer(
            model=model,
            args=args,
            train_dataset=dataset,
            tokenizer=processor,
            data_collator=collate_fn
        )

        logger.info("🚀 Starting training...")
        trainer.train()
        logger.info("✅ Training completed.")

        model.save_pretrained(output_dir, safe_serialization=False)
        model.save_pretrained(output_dir, safe_serialization=True)
        processor.save_pretrained(output_dir)
        logger.info(f"✅ Model saved to {output_dir}")

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"❌ Training failed:\n{error_trace}")
        return {"status": "❌ Training failed.", "stderr": error_trace}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, required=True, help="Task name (e.g., program_catalog, calendar, announcements)")
    args = parser.parse_args()
    train_donut_model(args.task)
