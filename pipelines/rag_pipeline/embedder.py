from __future__ import annotations

from threading import Lock

from .config import RagSettings


class EmbeddingService:
    _model = None
    _lock = Lock()
    _model_name: str | None = None

    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()

    def _get_model(self):
        with self._lock:
            if self.__class__._model is None or self.__class__._model_name != self.settings.embedding_model_name:
                try:
                    from fastembed import TextEmbedding
                except ImportError as exc:
                    raise RuntimeError(
                        "fastembed is required for the RAG embedding pipeline. "
                        "Install backend dependencies before using explanations."
                    ) from exc

                self.__class__._model = TextEmbedding(model_name=self.settings.embedding_model_name)
                self.__class__._model_name = self.settings.embedding_model_name
        return self.__class__._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._get_model()
        return [list(vector) for vector in model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0] if vectors else []
