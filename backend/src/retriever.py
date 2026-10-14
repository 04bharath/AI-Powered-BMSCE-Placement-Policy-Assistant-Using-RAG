"""Retrieval with distance-based relevance gating and optional reranking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .embeddings import Embedder
from .vector_store import DocumentRegistry, VectorStore


@dataclass
class RetrievedChunk:
    text: str
    document_id: str
    filename: str
    document_version: int
    page_number: int
    chunk_id: str
    distance: float
    rerank_score: float | None = None


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    candidates_considered: int = 0
    dropped_for_distance: int = 0
    reranked: bool = False
    best_distance: float | None = None

    def metadata(self) -> dict[str, Any]:
        return {
            "candidates_considered": self.candidates_considered,
            "dropped_for_distance": self.dropped_for_distance,
            "returned": len(self.chunks),
            "reranked": self.reranked,
            "best_distance": self.best_distance,
        }


class Retriever:
    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        registry: DocumentRegistry,
        *,
        top_k: int = 5,
        fetch_k: int = 12,
        max_distance: float = 0.75,
        reranker: Callable[[str, list[str]], list[float]] | None = None,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._registry = registry
        self._top_k = top_k
        self._fetch_k = max(fetch_k, top_k)
        self._max_distance = max_distance
        self._reranker = reranker

    def _current_versions(self) -> dict[str, int]:
        return {
            r.document_id: r.version
            for r in self._registry.list(include_archived=False)
            if r.status == "ready" and r.is_current
        }

    def retrieve(self, question: str) -> RetrievalResult:
        current = self._current_versions()
        if not current:
            return RetrievalResult()

        raw = self._store.query(self._embedder.embed_query(question), self._fetch_k)
        result = RetrievalResult(candidates_considered=len(raw))

        kept: list[RetrievedChunk] = []
        for item in raw:
            meta = item["metadata"]
            # Never surface archived/stale versions, even if vectors linger.
            if current.get(meta["document_id"]) != meta["document_version"]:
                continue
            if item["distance"] > self._max_distance:
                result.dropped_for_distance += 1
                continue
            kept.append(
                RetrievedChunk(
                    text=item["text"],
                    document_id=meta["document_id"],
                    filename=meta["filename"],
                    document_version=int(meta["document_version"]),
                    page_number=int(meta["page_number"]),
                    chunk_id=meta["chunk_id"],
                    distance=item["distance"],
                )
            )

        if kept and self._reranker is not None:
            scores = self._reranker(question, [c.text for c in kept])
            for c, s in zip(kept, scores):
                c.rerank_score = float(s)
            kept.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
            result.reranked = True
        else:
            kept.sort(key=lambda c: c.distance)

        result.chunks = kept[: self._top_k]
        result.best_distance = min((c.distance for c in kept), default=None)
        return result


def build_cross_encoder_reranker(model_name: str) -> Callable[[str, list[str]], list[float]]:
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(model_name)

    def _rerank(query: str, passages: list[str]) -> list[float]:
        return [float(s) for s in model.predict([(query, p) for p in passages])]

    return _rerank
