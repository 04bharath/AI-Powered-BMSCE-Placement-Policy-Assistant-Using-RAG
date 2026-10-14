"""Shared test fixtures: deterministic fake embedder/LLM and a synthetic policy PDF.

The synthetic policy is generated here, so the page numbers asserted in tests are
known by construction (not guessed about any real college document).
"""
from __future__ import annotations

import hashlib
import io
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from config import Settings  # noqa: E402
from src.rag_pipeline import RAGPipeline  # noqa: E402
from src.retriever import Retriever  # noqa: E402
from src.vector_store import DocumentRegistry, VectorStore  # noqa: E402

STOPWORDS = {
    "a", "an", "the", "of", "to", "is", "are", "be", "for", "in", "on", "and", "or",
    "what", "who", "how", "do", "does", "can", "that", "this", "with", "by", "at", "it",
}
DIM = 4096  # large enough that unrelated words rarely hash-collide


class FakeEmbedder:
    """Hashing bag-of-words embedder: deterministic, offline, cosine-friendly."""

    model_name = "fake-hash-embedder"

    def __init__(self, dim: int = DIM) -> None:
        self._dim = dim
        self.calls = 0

    @property
    def dimension(self) -> int:
        return self._dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self._dim
        for tok in re.findall(r"[a-z0-9.]+", text.lower()):
            if tok in STOPWORDS:
                continue
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % self._dim
            v[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts):
        self.calls += 1
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLM:
    model_name = "fake-llm"

    def __init__(self, reply: str = "Students need a minimum CGPA of 7.0 [policy.pdf, p. 1].") -> None:
        self.reply = reply
        self.calls: list[tuple[str, str]] = []
        self.available = True

    def generate(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        return self.reply

    def is_available(self) -> bool:
        return self.available


POLICY_PAGES = [
    "Placement Eligibility\n"
    "Students must hold a minimum CGPA of 7.0 and have no active backlogs to be eligible "
    "for campus placements. Eligibility is verified by the placement office before each drive.",
    "Offer Acceptance Rules\n"
    "A student who accepts a placement offer is not permitted to sit for further company drives. "
    "Withdrawing from an accepted offer leads to debarment from all placement activities.",
    "Internship Offers\n"
    "Internship offers must be reported to the placement office within seven days of receipt. "
    "Pre-placement offers from internships follow the standard offer acceptance rules.",
]


def make_pdf(pages: list[str] | None = None, blank_pages: set[int] | None = None) -> bytes:
    """Build a PDF. `blank_pages` are 1-based indexes that are left without text."""
    pages = pages if pages is not None else POLICY_PAGES
    blank_pages = blank_pages or set()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i, text in enumerate(pages, start=1):
        if i not in blank_pages:
            y = 800
            for line in text.split("\n"):
                # naive wrap at ~90 chars
                words, cur = line.split(" "), ""
                for w in words:
                    if len(cur) + len(w) + 1 > 90:
                        c.drawString(50, y, cur)
                        y -= 16
                        cur = w
                    else:
                        cur = f"{cur} {w}".strip()
                c.drawString(50, y, cur)
                y -= 16
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def policy_pdf() -> bytes:
    return make_pdf()


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        chroma_dir=tmp_path / "chroma",
        upload_dir=tmp_path / "uploads",
        registry_path=tmp_path / "chroma" / "registry.json",
        collection_name="test_policy",
        allowed_origins=["http://localhost:3000"],
        max_upload_mb=1,
        chunk_size=300,
        chunk_overlap=50,
        top_k=4,
        fetch_k=10,
        max_distance=0.9,
        admin_token="test-admin-token",
    )


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def pipeline(settings, embedder, llm) -> RAGPipeline:
    store = VectorStore(settings.chroma_dir, settings.collection_name, embedder.model_name, embedder.dimension)
    registry = DocumentRegistry(settings.registry_path)
    retriever = Retriever(
        store, embedder, registry,
        top_k=settings.top_k, fetch_k=settings.fetch_k, max_distance=settings.max_distance,
    )
    return RAGPipeline(
        store=store, registry=registry, embedder=embedder, retriever=retriever, llm=llm,
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap,
    )


@pytest.fixture
def indexed(pipeline, policy_pdf):
    pipeline.ingest_pdf(policy_pdf, "policy.pdf")
    return pipeline
