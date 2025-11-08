from __future__ import annotations
import json, os
from pathlib import Path
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
import torch

# --------- Paths & model choice ----------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "finetune" / "pa_examples.jsonl"
BASE = os.getenv("BASE_FT_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")  # open, good on M2
OUT  = ROOT / "models" / "pa-lora"

MAX_LEN = int(os.getenv("FT_MAX_LEN", "1536"))  # trim if OOM; 1024 is safer, 1536 is OK for TinyLlama

# --------- Data prep ----------
def load_ds():
    rows=[]
    with open(DATA) as f:
        for line in f:
            ex=json.loads(line)
            prompt = (
                f"### Instruction:\n{ex['instruction']}\n\n"
                f"### Patient Summary:\n{json.dumps(ex['input']['patient_summary'], indent=2)}\n\n"
                "### Policy Passages:\n" + "\n".join(p['text'] for p in ex['input']['policy_passages']) +
                "\n\n### Requested Service:\n" + ex['input']['requested_service'] +
                "\n\n### Response:\n"
            )
            rows.append({"text": prompt + ex['output']})
    return Dataset.from_list(rows)

def make_collator(tokenizer):
    def collate(batch):
        texts = [b["text"] for b in batch]
        enc = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=MAX_LEN,
            return_tensors="pt",
        )
        # LM loss on all tokens
        enc["labels"] = enc["input_ids"].clone()
        return enc
    return collate

def main():
    ds = load_ds()

    tok = AutoTokenizer.from_pretrained(BASE, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # Device choice: prefer Apple MPS if available; else CPU
    use_mps = torch.backends.mps.is_available()
    dtype = torch.float32  # MPS works more reliably in fp32
    model = AutoModelForCausalLM.from_pretrained(
        BASE,
        torch_dtype=dtype,
        device_map="mps" if use_mps else None,  # CPU if no MPS
    )

    # LoRA adapter
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj","v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)

    # Training args — IMPORTANT: remove_unused_columns=False
    args = TrainingArguments(
        output_dir=str(OUT),
        num_train_epochs=2,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        report_to=[],
        fp16=False,                       # keep False on MPS/CPU
        remove_unused_columns=False,      # <- fixes your error
        dataloader_pin_memory=False,      # safer for MPS/CPU
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds,
        data_collator=make_collator(tok),
    )

    trainer.train()
    model.save_pretrained(str(OUT))
    tok.save_pretrained(str(OUT))
    print("✅ saved:", OUT)

if __name__ == "__main__":
    main()
