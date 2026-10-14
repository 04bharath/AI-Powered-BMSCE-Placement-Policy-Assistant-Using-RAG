"""ChromaDB storage plus a JSON document registry for versions and status."""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

from .chunking import Chunk


class EmbeddingMismatchError(RuntimeError):
    """The persisted collection was built with a different embedding model/dimension."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return slug or "document"


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
@dataclass
class DocumentRecord:
    document_id: str
    version: int
    filename: str
    content_hash: str
    status: str  # "indexing" | "ready" | "failed" | "archived"
    is_current: bool = True
    page_count: int | None = None
    pages_with_text: int | None = None
    chunk_count: int | None = None
    uploaded_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    embedding_model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DocumentRegistry:
    """Small, atomic, thread-safe JSON registry of document versions."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[DocumentRecord] = self._read()

    def _read(self) -> list[DocumentRecord]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return [DocumentRecord(**r) for r in raw]
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError(f"Corrupt document registry at {self._path}: {exc}") from exc

    def _write(self) -> None:
        payload = json.dumps([r.to_dict() for r in self._records], indent=2)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, self._path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def list(self, include_archived: bool = True) -> list[DocumentRecord]:
        with self._lock:
            recs = [r for r in self._records if include_archived or r.status != "archived"]
            return sorted(recs, key=lambda r: (r.document_id, -r.version))

    def current(self, document_id: str) -> DocumentRecord | None:
        with self._lock:
            matches = [r for r in self._records if r.document_id == document_id and r.is_current]
            return max(matches, key=lambda r: r.version) if matches else None

    def find_by_hash(self, content_hash: str) -> DocumentRecord | None:
        with self._lock:
            for r in self._records:
                if r.content_hash == content_hash and r.status in {"ready", "indexing"}:
                    return r
            return None

    def next_version(self, document_id: str) -> int:
        with self._lock:
            versions = [r.version for r in self._records if r.document_id == document_id]
            return (max(versions) + 1) if versions else 1

    def add(self, record: DocumentRecord) -> None:
        with self._lock:
            self._records.append(record)
            self._write()

    def update(self, document_id: str, version: int, **changes: Any) -> DocumentRecord:
        with self._lock:
            for r in self._records:
                if r.document_id == document_id and r.version == version:
                    for k, v in changes.items():
                        setattr(r, k, v)
                    r.updated_at = utcnow()
                    self._write()
                    return r
            raise KeyError(f"{document_id} v{version} not found")

    def remove_document(self, document_id: str) -> int:
        with self._lock:
            before = len(self._records)
            self._records = [r for r in self._records if r.document_id != document_id]
            self._write()
            return before - len(self._records)

    def ready_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if r.status == "ready" and r.is_current)


# --------------------------------------------------------------------------- #
# Vector store
# --------------------------------------------------------------------------- #
class VectorStore:
    def __init__(
        self,
        persist_dir: Path,
        collection_name: str,
        embedding_model: str,
        embedding_dimension: int,
    ) -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._embedding_model = embedding_model
        self._dimension = embedding_dimension
        self._collection = self._open(collection_name)

    def _open(self, name: str):
        wanted = {
            "hnsw:space": "cosine",
            "embedding_model": self._embedding_model,
            "embedding_dimension": self._dimension,
        }
        existing = {c if isinstance(c, str) else c.name for c in self._client.list_collections()}
        if name in existing:
            col = self._client.get_collection(name)
            meta = col.metadata or {}
            if (
                meta.get("embedding_model") != self._embedding_model
                or meta.get("embedding_dimension") != self._dimension
            ):
                raise EmbeddingMismatchError(
                    f"Collection '{name}' was built with model "
                    f"'{meta.get('embedding_model')}' (dim {meta.get('embedding_dimension')}), "
                    f"but the configured model is '{self._embedding_model}' (dim {self._dimension}). "
                    "Use a new CHROMA_COLLECTION / CHROMA_PERSIST_DIR or re-index all documents."
                )
            return col
        return self._client.create_collection(name, metadata=wanted)

    @property
    def collection(self):
        return self._collection

    def count(self) -> int:
        return self._collection.count()

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        for vec in embeddings:
            if len(vec) != self._dimension:
                raise EmbeddingMismatchError(
                    f"Embedding dimension {len(vec)} does not match collection ({self._dimension})."
                )
        batch = 256
        for i in range(0, len(chunks), batch):
            part = chunks[i : i + batch]
            self._collection.add(
                ids=[c.chunk_id for c in part],
                documents=[c.text for c in part],
                embeddings=embeddings[i : i + batch],
                metadatas=[c.metadata() for c in part],
            )

    def delete_document(self, document_id: str, version: int | None = None) -> None:
        where: dict[str, Any] = {"document_id": document_id}
        if version is not None:
            where = {"$and": [{"document_id": document_id}, {"document_version": version}]}
        self._collection.delete(where=where)

    def query(
        self, embedding: list[float], n_results: int, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        total = self._collection.count()
        if total == 0:
            return []
        res = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: list[dict[str, Any]] = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            out.append({"text": doc, "metadata": meta, "distance": float(dist)})
        return out
