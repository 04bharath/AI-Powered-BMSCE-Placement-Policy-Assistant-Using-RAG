"""Embedding backends. The Sentence Transformers model is loaded lazily."""
from __future__ import annotations

from typing import Protocol, Sequence


class Embedder(Protocol):
    model_name: str

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        self.model_name = model_name
        self._batch_size = batch_size
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        model = self._load()
        getter = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
        return int(getter())

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._load().encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
