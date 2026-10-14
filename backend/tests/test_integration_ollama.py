"""Opt-in tests against the real Ollama server and real embedding model.

Run with:  RUN_INTEGRATION=1 pytest -m integration
"""
import os

import pytest

from config import get_settings
from src.llm import SYSTEM_PROMPT, OllamaLLM

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"),
]


def test_real_ollama_answers_from_context():
    s = get_settings()
    llm = OllamaLLM(s.ollama_base_url, s.llm_model, 0.0, s.llm_timeout_seconds)
    if not llm.is_available():
        pytest.skip(f"Ollama model {s.llm_model} not reachable at {s.ollama_base_url}")
    prompt = (
        '<excerpt id="1" document="policy.pdf" page="4">Students need a minimum CGPA of 7.0.</excerpt>\n'
        "Student question: What CGPA is required?\nDo not include filenames, page numbers, or citations."
    )
    out = llm.generate(SYSTEM_PROMPT, prompt)
    assert "7.0" in out


def test_real_embedding_model_dimension_and_similarity():
    pytest.importorskip("sentence_transformers")
    from src.embeddings import SentenceTransformerEmbedder

    emb = SentenceTransformerEmbedder(get_settings().embedding_model)
    a, b, c = emb.embed_documents(
        ["minimum CGPA for placement eligibility", "CGPA cutoff to sit for campus drives", "banana bread recipe"]
    )
    assert len(a) == emb.dimension
    dot = lambda x, y: sum(i * j for i, j in zip(x, y))
    assert dot(a, b) > dot(a, c)
