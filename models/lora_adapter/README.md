# LoRA Adapter Output

`pipelines/llm_pipeline/train_lora.py` saves the optional clinical-chat PEFT adapter here by default.

Expected generated files after training include:

- `adapter_config.json`
- `adapter_model.safetensors`
- `training_metadata.json`
- `Modelfile`

The backend only tries the adapter-backed Ollama model when `LLM_LORA_ENABLED=true`, this directory contains adapter files, and `OLLAMA_LORA_MODEL` is configured.
