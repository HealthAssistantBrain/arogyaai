from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "data" / "llm_dataset" / "clinical_conversations.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "lora_adapter"
DEFAULT_BASE_MODEL = os.getenv("LORA_BASE_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

SYSTEM_PROMPT = (
    "You are ArogyaAI's clinical assistant. Behave like a careful doctor-style assistant: "
    "listen first, reason through triage clearly, ask focused follow-up questions, use patient data and retrieved medical context, "
    "avoid overconfidence, never claim a final diagnosis, and escalate critical symptoms."
)

DEFAULT_TARGET_MODULES = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)


def read_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError(f"line {line_number}: expected JSON object")
            missing = [key for key in ("instruction", "input", "output") if not isinstance(payload.get(key), str)]
            if missing:
                raise ValueError(f"line {line_number}: missing string keys: {', '.join(missing)}")
            rows.append(
                {
                    "instruction": payload["instruction"].strip(),
                    "input": payload["input"].strip(),
                    "output": payload["output"].strip(),
                }
            )
    if not rows:
        raise ValueError(f"No training rows found in {path}")
    return rows


def format_prompt(record: dict[str, str]) -> tuple[str, str]:
    prompt = (
        "<s>[INST] <<SYS>>\n"
        f"{SYSTEM_PROMPT}\n"
        "<</SYS>>\n\n"
        f"Instruction:\n{record['instruction']}\n\n"
        f"Patient context:\n{record['input']}\n\n"
        "Respond with cautious doctor-style guidance. Include triage thinking, 1-2 follow-up questions when useful, "
        "clear next steps, safety escalation for red flags, and no diagnosis claim.\n"
        "[/INST]\n"
    )
    completion = f"{record['output'].strip()}</s>"
    return prompt, completion


class ClinicalConversationDataset:
    def __init__(self, rows: list[dict[str, str]], tokenizer: Any, max_length: int) -> None:
        self.features = [self._encode(row, tokenizer, max_length) for row in rows]

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.features[index]

    @staticmethod
    def _encode(record: dict[str, str], tokenizer: Any, max_length: int) -> dict[str, list[int]]:
        prompt, completion = format_prompt(record)
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        full_ids = tokenizer(prompt + completion, add_special_tokens=False, truncation=True, max_length=max_length)["input_ids"]
        prompt_length = min(len(prompt_ids), len(full_ids))
        labels = [-100] * prompt_length + full_ids[prompt_length:]
        return {
            "input_ids": full_ids,
            "attention_mask": [1] * len(full_ids),
            "labels": labels,
        }


@dataclass
class CausalLMCollator:
    tokenizer: Any

    def __call__(self, features: list[dict[str, list[int]]]) -> dict[str, Any]:
        import torch

        max_length = max(len(feature["input_ids"]) for feature in features)
        pad_token_id = self.tokenizer.pad_token_id
        batch = {"input_ids": [], "attention_mask": [], "labels": []}

        for feature in features:
            pad_length = max_length - len(feature["input_ids"])
            batch["input_ids"].append(feature["input_ids"] + [pad_token_id] * pad_length)
            batch["attention_mask"].append(feature["attention_mask"] + [0] * pad_length)
            batch["labels"].append(feature["labels"] + [-100] * pad_length)

        return {key: torch.tensor(value, dtype=torch.long) for key, value in batch.items()}


def _parse_target_modules(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_training_stack() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    except ImportError as exc:
        raise RuntimeError(
            "LoRA training dependencies are missing. Install them with "
            "`python -m pip install -r pipelines/llm_pipeline/requirements.txt`."
        ) from exc
    return torch, LoraConfig, get_peft_model, (AutoModelForCausalLM, AutoTokenizer), (Trainer, TrainingArguments)


def _torch_dtype(torch: Any) -> Any:
    if not torch.cuda.is_available():
        return torch.float32
    if torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float16


def write_metadata(
    *,
    output_dir: Path,
    dataset_path: Path,
    base_model: str,
    ollama_from_model: str,
    target_modules: list[str],
    rows: int,
    args: argparse.Namespace,
) -> None:
    metadata = {
        "base_model": base_model,
        "ollama_from_model": ollama_from_model,
        "dataset": str(dataset_path),
        "rows": rows,
        "adapter_type": "peft_lora",
        "target_modules": target_modules,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": args.lora_dropout,
        "max_length": args.max_length,
        "doctor_style_guardrails": [
            "ask focused follow-up questions",
            "summarize triage thinking without a final diagnosis claim",
            "escalate critical symptoms",
            "use ML and RAG context when supplied by the chat service",
        ],
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def write_ollama_modelfile(output_dir: Path, base_model: str) -> None:
    adapter_name = "adapter_model.safetensors"
    if not (output_dir / adapter_name).exists() and (output_dir / "adapter_model.bin").exists():
        adapter_name = "adapter_model.bin"

    modelfile = f'''FROM {base_model}
ADAPTER ./{adapter_name}
PARAMETER temperature 0.2
PARAMETER top_p 0.85
SYSTEM """{SYSTEM_PROMPT}"""
'''
    (output_dir / "Modelfile").write_text(modelfile, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an optional PEFT LoRA adapter for ArogyaAI clinical chat.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help="Any llama-compatible causal LM or local model path.")
    parser.add_argument("--ollama-from-model", default=os.getenv("OLLAMA_MODEL", "llama3.1:8b"), help="Ollama base model used in the generated Modelfile.")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", default=",".join(DEFAULT_TARGET_MODULES))
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch, LoraConfig, get_peft_model, model_classes, trainer_classes = _load_training_stack()
    AutoModelForCausalLM, AutoTokenizer = model_classes
    Trainer, TrainingArguments = trainer_classes

    rows = read_jsonl(args.dataset)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model_kwargs: dict[str, Any] = {"torch_dtype": _torch_dtype(torch)}
    if torch.cuda.is_available():
        model_kwargs["device_map"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(args.base_model, **model_kwargs)
    model.config.use_cache = False
    if args.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    target_modules = _parse_target_modules(args.target_modules)
    lora_config = LoraConfig(
        task_type="CAUSAL_LM",
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_dataset = ClinicalConversationDataset(rows, tokenizer, args.max_length)
    use_bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    use_fp16 = bool(torch.cuda.is_available() and not use_bf16)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=2,
        save_safetensors=True,
        report_to=[],
        remove_unused_columns=False,
        optim="adamw_torch",
        bf16=use_bf16,
        fp16=use_fp16,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=CausalLMCollator(tokenizer),
    )
    trainer.train()
    model.save_pretrained(args.output_dir, safe_serialization=True)
    tokenizer.save_pretrained(args.output_dir)
    write_metadata(
        output_dir=args.output_dir,
        dataset_path=args.dataset,
        base_model=args.base_model,
        ollama_from_model=args.ollama_from_model,
        target_modules=target_modules,
        rows=len(rows),
        args=args,
    )
    write_ollama_modelfile(args.output_dir, args.ollama_from_model)
    print(f"Saved LoRA adapter to {args.output_dir}")
    print(f"Optional Ollama Modelfile written to {args.output_dir / 'Modelfile'}")


if __name__ == "__main__":
    main()
