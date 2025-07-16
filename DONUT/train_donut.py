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
import torch
from pdf2image import convert_from_path

# -------------------------------
# Logging Setup
# -------------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# -------------------------------
# CONFIGURATION
# -------------------------------
MODEL_NAME = "naver-clova-ix/donut-base-finetuned-docvqa"
#MAX_TRAIN_SAMPLES = 30
NUM_EPOCHS = 4
MAX_LENGTH = 768
# DPI should match the DPI used when preparing images in prepare_all_training_data
# If your prepare_all_training_data used 150 DPI, keep it consistent.
DPI = 200

# Define root directories for prepared data and output models
JSONL_ROOT = Path("/app/training_jsonl") # Where .jsonl files (image_path, ground_truth) are stored
OUTPUT_BASE_DIR = Path("./donut-finetuned") # Where trained models will be saved

# Initialize processor globally once
processor = DonutProcessor.from_pretrained(MODEL_NAME)
# -------------------------------
# clasisfying document type and stitch pdfs
# -------------------------------
def classify_document_type(text: str) -> str:
    text = text.lower()
    if "program catalog" in text or "bachelor of" in text:
        return "program_catalog"
    elif "academic calendar" in text or "holiday" in text or "semester" in text:
        return "academic_calendar"
    elif "announcement" in text or "attention" in text:
        return "announcement"
    else:
        return "unknown"

def stitch_pdf_to_image(pdf_path):
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

# -------------------------------
# Data Loading (Modified to read from .jsonl files)
# -------------------------------
def load_training_examples(jsonl_path: Path, limit=None):
    """
    Loads training examples directly from a .jsonl file, which should contain
    paths to pre-processed images and their corresponding JSON ground truths.
    """
    logger.info(f"📚 Loading training examples from JSONL: {jsonl_path}...")
    data = []

    if not jsonl_path.exists():
        logger.error(f"❌ JSONL file not found: {jsonl_path}")
        return []

    # Infer task_name from the jsonl_path (e.g., 'ProgCat' from 'ProgCat.jsonl')
    task_name = jsonl_path.stem

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            if limit and len(data) >= limit:
                break
            try:
                entry = json.loads(line)
                image_path = Path(entry["image"])
                ground_truth = entry["ground_truth"]

                if not image_path.exists():
                    logger.warning(f"⚠️ Image missing for entry in {jsonl_path} line {line_num+1}: {image_path}, skipping.")
                    continue

                # Open the pre-processed image (e.g., the stitched PNG)
                image = Image.open(image_path)
                if image.mode != "RGB":
                    image = image.convert("RGB")

                # Customize task prompt based on the document type (task_name)
                # This prompt is crucial for Donut to understand the extraction task for this specific type
                task_prompt = f"<s_docvqa><s_question>extract structured JSON for {task_name} document</s_question><s_answer>"

                data.append({
                    "image": image,
                    "task_prompt": task_prompt,
                    "ground_truth": ground_truth
                })
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Invalid JSON in {jsonl_path} line {line_num+1}: {e}, skipping.")
            except Exception as e:
                logger.warning(f"⚠️ Error processing entry in {jsonl_path} line {line_num+1}: {e}, skipping.")

    logger.info(f"✅ Loaded {len(data)} training samples from {jsonl_path.name}.")
    return data

# -------------------------------
# Preprocessing (Remains the same)
# -------------------------------
def preprocess_example(example):
    image = example["image"]
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
    labels[labels == processor.tokenizer.pad_token_id] = -100 # Mask padding tokens
    return {
        "pixel_values": pixel_values,
        "labels": labels
    }

# -------------------------------
# Collate Function (Remains the same)
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
# Training Function (Modified to use .jsonl paths)
# -------------------------------
def train_donut_model(task_name: str):
    """
    Trains a Donut model for a specific document type (task_name).
    Assumes .jsonl training data for this task is already prepared
    and located at {JSONL_ROOT}/{task_name}.jsonl.
    """
    try:
        logger.info(f"⏳ Initializing model for training task: {task_name}...")

        # Construct the path to the .jsonl file for this specific task
        jsonl_path_for_task = JSONL_ROOT / f"{task_name}.jsonl"

        # Construct the output directory for this trained model
        output_dir = OUTPUT_BASE_DIR / task_name
        output_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

        model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

        # Handle special tokens and model configuration
        if "<s_docvqa>" not in processor.tokenizer.get_vocab():
            processor.tokenizer.add_special_tokens({"additional_special_tokens": ["<s_docvqa>"]})
            model.decoder.resize_token_embeddings(len(processor.tokenizer))

        # Adjust position embeddings (Crucial for handling longer sequences)
        # MAX_LENGTH + 2 is a common heuristic (for EOS and potentially start tokens)
        if MAX_LENGTH + 2 > model.decoder.config.max_position_embeddings:
            logger.info(f"Adjusting decoder max_position_embeddings from {model.decoder.config.max_position_embeddings} to {MAX_LENGTH + 2}")
            from transformers.models.mbart.modeling_mbart import MBartLearnedPositionalEmbedding
            model.decoder.model.decoder.embed_positions = MBartLearnedPositionalEmbedding(
                MAX_LENGTH + 2,
                model.decoder.config.d_model
            )
            model.decoder.config.max_position_embeddings = MAX_LENGTH + 2

        model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids("<s_docvqa>")
        model.config.pad_token_id = processor.tokenizer.pad_token_id
        model.config.eos_token_id = processor.tokenizer.eos_token_id
        model.config.vocab_size = len(processor.tokenizer)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)

        # Load samples using the .jsonl path for the current task
        samples = load_training_examples(jsonl_path_for_task)
        if not samples:
            raise ValueError(f"❌ No training samples found in {jsonl_path_for_task}. Cannot train model for {task_name}.")

        dataset = Dataset.from_list(samples)
        dataset = dataset.map(preprocess_example, remove_columns=["image", "task_prompt", "ground_truth"])
        dataset.set_format("torch")
        logger.info("✅ Dataset format set to 'torch'.")

        args = Seq2SeqTrainingArguments(
            output_dir=str(output_dir), # Convert Path to string for HuggingFace args
            per_device_train_batch_size=1,
            evaluation_strategy="no", # No evaluation during training
            num_train_epochs=NUM_EPOCHS,
            learning_rate=2e-5,
            save_strategy="epoch", # Save checkpoints after each epoch
            logging_dir=os.path.join(str(output_dir), "logs"), # Logs specific to this output_dir
            predict_with_generate=True,
            remove_unused_columns=False,
            fp16=False,
            logging_strategy = "steps",
            logging_steps=10,
            save_total_limit=2, # Keep only the last 2 checkpoints
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

        logger.info(f"🚀 Starting training for {task_name}...")
        trainer.train()
        logger.info(f"✅ Training for {task_name} completed.")

        # Save the final model and processor for this task
        model.save_pretrained(output_dir, safe_serialization=True)
        processor.save_pretrained(output_dir)
        logger.info(f"✅ Model and processor for {task_name} saved to {output_dir}")

        return { "status": f"✅ Donut model trained successfully for '{task_name}' type." }

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"❌ Training failed for '{task_name}' type:\n{error_trace}")
        return { "status": "❌ Training failed.", "stderr": error_trace }

# -------------------------------
# Main Entry Point for Script Execution
# -------------------------------
if __name__ == "__main__":
    logger.info("--- Starting Donut Model Training for All Document Types ---")

    # Ensure the base directory for output models exists
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Check if the JSONL root directory exists and contains prepared data
    if not JSONL_ROOT.exists():
        logger.error(f"❌ JSONL root directory not found: {JSONL_ROOT}.")
        logger.info("Please ensure you have run the '/prepare/training-data' API endpoint to generate .jsonl files first.")
    else:
        # Iterate through all .jsonl files in the JSONL_ROOT to get each task_name
        trained_tasks = []
        jsonl_files_found = list(JSONL_ROOT.glob("*.jsonl"))

        if not jsonl_files_found:
            logger.warning(f"⚠️ No .jsonl files found in {JSONL_ROOT}. Nothing to train.")
        else:
            for jsonl_file in jsonl_files_found:
                # The task_name is derived from the filename of the .jsonl file (e.g., "ProgCat" from "ProgCat.jsonl")
                task_name = jsonl_file.stem

                logger.info(f"\n--- Initiating training for document type: {task_name} ---")
                result = train_donut_model(task_name)

                if "status" in result and "✅" in result["status"]:
                    trained_tasks.append(task_name)
                else:
                    logger.error(f"Failed to train model for {task_name}. Details: {result.get('stderr', 'No error details provided.')}")

            if trained_tasks:
                logger.info(f"\n--- Successfully trained models for the following document types: {', '.join(trained_tasks)} ---")
            else:
                logger.warning("\n--- No Donut models were successfully trained. Check logs for errors. ---")