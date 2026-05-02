# ArogyaAI Clinical LoRA Pipeline

This pipeline trains an optional PEFT LoRA adapter that teaches the chat model a cautious doctor-style response pattern. It does not replace the base LLM.

## Files

- `data/llm_dataset/clinical_conversations.jsonl`: seed instruction dataset with symptoms, vitals, follow-up questions, triage language, and safety escalation.
- `pipelines/llm_pipeline/validate_dataset.py`: JSONL and safety-shape validation.
- `pipelines/llm_pipeline/train_lora.py`: PEFT/Transformers LoRA trainer.
- `models/lora_adapter/`: default adapter output directory.

## Train

Install training dependencies in a separate environment from the backend if possible:

```bash
python -m pip install -r pipelines/llm_pipeline/requirements.txt
```

Validate the seed data:

```bash
python -m pipelines.llm_pipeline.validate_dataset --dataset data/llm_dataset/clinical_conversations.jsonl
```

Train on a llama-compatible causal LM:

```bash
python -m pipelines.llm_pipeline.train_lora \
  --base-model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --ollama-from-model tinyllama \
  --dataset data/llm_dataset/clinical_conversations.jsonl \
  --output-dir models/lora_adapter \
  --batch-size 1 \
  --gradient-accumulation-steps 8
```

The script saves PEFT adapter files and a starter `Modelfile` into `models/lora_adapter/`.
For production, train the adapter on the same base family you will serve through Ollama; for example, an adapter trained on a Llama 3.1 8B Hugging Face base should be attached to the matching Llama 3.1 8B Ollama base.

## Optional Ollama Use

Create an adapter-backed Ollama model after training:

```bash
ollama create arogyaai-clinical -f models/lora_adapter/Modelfile
```

Then enable the optional layer for the backend:

```bash
LLM_LORA_ENABLED=true
LLM_LORA_ADAPTER_PATH=models/lora_adapter
OLLAMA_LORA_MODEL=arogyaai-clinical
```

If the adapter directory is missing, `OLLAMA_LORA_MODEL` is blank, or the adapter-backed Ollama request fails, `chat_service.py` falls back to `OLLAMA_MODEL`.
