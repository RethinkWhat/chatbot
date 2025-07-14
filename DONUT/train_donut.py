# train_donut.py
import os, io, contextlib, traceback
import json
import traceback
import logging
from pathlib import Path
from datasets import Dataset, Features, Value, Array3D
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
DATA_DIR = "./datasets"
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
JSON_DIR = os.path.join(DATA_DIR, "labels")
OUTPUT_DIR = "./donut-finetuned"
MAX_TRAIN_SAMPLES = 20
NUM_EPOCHS = 3
# Initialize processor globally once
processor = DonutProcessor.from_pretrained(MODEL_NAME)

# -------------------------------
# Data Loading
# -------------------------------
def load_training_examples(pdf_dir, json_dir, limit=None):
    logger.info("📚 Loading training examples...")
    data = []
    for json_file in Path(json_dir).glob("*.json"):
        base = json_file.stem
        pdf_path = Path(pdf_dir) / f"{base}.pdf"
        if not pdf_path.exists():
            logger.warning(f"⚠️ PDF missing for {json_file.name}")
            continue

        pages = convert_from_path(str(pdf_path), dpi=150) # Keep DPI at 150
        with open(json_file, "r", encoding="utf-8") as f:
            label = json.load(f)

        for i, img in enumerate(pages):
            data.append({
                "image": img,
                "task_prompt": "<s_docvqa><s_question>extract information</s_question><s_answer>",
                "ground_truth": json.dumps(label, ensure_ascii=False)
            })

            if limit and len(data) >= limit:
                break

        if limit and len(data) >= limit:
            break

    logger.info(f"✅ Loaded {len(data)} training samples.")
    return data


# -------------------------------
# Preprocessing
# -------------------------------
def preprocess_example(example):
    image = example["image"]
    if not isinstance(image, Image.Image):
        # This fallback should ideally not be hit if convert_from_path works
        image = Image.open(image).convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")

    pixel_values = processor.image_processor(image, return_tensors="pt").pixel_values.squeeze(0)
    # Tokenize prompt + label
    text = example["task_prompt"] + example["ground_truth"]
    tokenized = processor.tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        max_length=512,
        truncation=True
    )
    labels = tokenized.input_ids.squeeze(0)

    # Mask pad token IDs
    labels[labels == processor.tokenizer.pad_token_id] = -100
    if (labels >= processor.tokenizer.vocab_size).any():
        logger.warning("⚠️ Some labels exceed vocab size after masking.")
    # Debug check
    logger.debug(f"Max label ID: {labels.max().item()} / Vocab size: {processor.tokenizer.vocab_size}")

    return {
        "pixel_values": pixel_values,
        "labels": labels
    }


def collate_fn(batch):
    logger.debug(f"DEBUG_COLLATE: Entering collate_fn. Batch size: {len(batch)}")
    for i, x in enumerate(batch):
        # Safely inspect batch items before attempting operations that require tensors
        pixel_val_obj = x.get('pixel_values')
        label_obj = x.get('labels')

        logger.debug(f"DEBUG_COLLATE: Item {i} pixel_values type: {type(pixel_val_obj)}")
        logger.debug(f"DEBUG_COLLATE: Item {i} labels type: {type(label_obj)}")

        # Print shape only if it's a tensor, otherwise print N/A
        if isinstance(pixel_val_obj, torch.Tensor):
            logger.debug(f"DEBUG_COLLATE: Item {i} pixel_values shape: {pixel_val_obj.shape}")
        if isinstance(label_obj, torch.Tensor):
            logger.debug(f"DEBUG_COLLATE: Item {i} labels shape: {label_obj.shape}")


    # These lines will now attempt to stack/pad.
    # If the error still occurs here, the issue is that items in 'batch' are lists.
    pixel_values = torch.stack([x["pixel_values"] for x in batch])
    labels = torch.nn.utils.rnn.pad_sequence(
        [x["labels"] for x in batch],
        batch_first=True,
        padding_value=processor.tokenizer.pad_token_id
    )
    logger.debug(f"DEBUG_COLLATE: Stacked pixel_values shape: {pixel_values.shape}, labels shape: {labels.shape}")
    return {"pixel_values": pixel_values, "labels": labels}


# -------------------------------
# Training Entry Point
# -------------------------------
def train_donut_model():
    # Removed contextlib.redirect_stdout/stderr to allow direct log output in Docker
    try:
        logger.info("⏳ Initializing model...")
        model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

        #SPECIAL token
        if "<s_docvqa>" not in processor.tokenizer.get_vocab():
            special_tokens_dict = {"additional_special_tokens": ["<s_docvqa>"]}
            processor.tokenizer.add_special_tokens(special_tokens_dict)
            model.decoder.resize_token_embeddings(len(processor.tokenizer))

        from transformers.models.mbart.modeling_mbart import MBartLearnedPositionalEmbedding
        MAX_NEW_POSITION_EMBEDDINGS = 1536  # or higher if needed

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

        samples = load_training_examples(PDF_DIR, JSON_DIR, limit=MAX_TRAIN_SAMPLES)
        if not samples:
            raise ValueError("❌ No training samples found in datasets.")

        dataset = Dataset.from_list(samples)  # ✅ Defined once

        # Log raw structure
        logger.debug(f"DEBUG_DATASET_INIT: First raw sample (before map): {samples[0].keys()}")

        # Preprocess the dataset (produces 'pixel_values' and 'labels')
        logger.info("🔁 Preprocessing dataset with map...")
        dataset = dataset.map(preprocess_example, remove_columns=["image", "task_prompt", "ground_truth"])
        # tokenization is done here
        max_label_id = max([max(example['labels']) for example in dataset])
        logger.debug(f"📏 Max label ID in dataset: {max_label_id}")
        logger.debug(f"📚 Tokenizer vocab size: {len(processor.tokenizer)}")
        logger.debug(f"📐 Decoder embedding size: {model.config.vocab_size}")
        assert max_label_id < len(processor.tokenizer), "❌ Token ID out of bounds!"


        # Log structure after map
        logger.debug(f"DEBUG_DATASET_AFTER_MAP: First element of dataset: {dataset[0].keys()}")
        logger.debug(f"DEBUG_DATASET_AFTER_MAP: Type of pixel_values in first element: {type(dataset[0]['pixel_values'])}")
        logger.debug(f"DEBUG_DATASET_AFTER_MAP: Type of labels in first element: {type(dataset[0]['labels'])}")

        # Set format for PyTorch
        dataset.set_format("torch") 
        logger.info("✅ Dataset format set to 'torch'.")

        # Log content of first item after map to see processed structure
        logger.debug(f"DEBUG_DATASET_AFTER_MAP: First element of dataset: {dataset[0].keys()}")
        logger.debug(f"DEBUG_DATASET_AFTER_MAP: Type of pixel_values in first element: {type(dataset[0]['pixel_values'])}")
        logger.debug(f"DEBUG_DATASET_AFTER_MAP: Type of labels in first element: {type(dataset[0]['labels'])}")
        
        logger.info(f"🧾 Dataset columns after map and remove: {dataset.column_names}")
        # Note: Printing dataset[0] directly might re-trigger processing if not cached
        # logger.info(f"🧾 Example first element after map: {dataset[0]}")


        args = Seq2SeqTrainingArguments(
            output_dir=OUTPUT_DIR,
            per_device_train_batch_size=1,
            num_train_epochs=NUM_EPOCHS,
            learning_rate=5e-5,
            save_strategy="epoch",
            logging_dir="./logs",
            predict_with_generate=True,
            remove_unused_columns=False, # Keep this to retain pixel_values, labels
            fp16=torch.cuda.is_available()
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
        model.save_pretrained(OUTPUT_DIR)
        processor.save_pretrained(OUTPUT_DIR)
        logger.info(f"✅ Training completed. Model saved to {OUTPUT_DIR}")

        return { "status": "✅ Donut model trained successfully." }

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"❌ Training failed:\n{error_trace}")
        return { "status": "❌ Training failed.", "stderr": error_trace }

# -------------------------------
# Main Entry Point for Script Execution
# -------------------------------
if __name__ == "__main__":
    train_donut_model()