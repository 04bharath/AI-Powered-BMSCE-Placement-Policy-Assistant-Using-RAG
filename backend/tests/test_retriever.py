import json
from pathlib import Path

import pytest

from src.retriever import Retriever
from src.vector_store import EmbeddingMismatchError, VectorStore

from .conftest import FakeEmbedder

EVAL = json.loads((Path(__file__).parent / "eval_questions.json").read_text())


# ---------------------------------------------------------------- embeddings
def test_embeddings_have_expected_shape_and_are_normalised(embedder):
    vecs = embedder.embed_documents(["minimum cgpa", "internship offers"])
    assert len(vecs) == 2 and all(len(v) == embedder.dimension for v in vecs)
    assert all(abs(sum(x * x for x in v) - 1.0) < 1e-6 for v in vecs)
    assert embedder.embed_query("minimum cgpa") == vecs[0]


# ------------------------------------------------------- storage + retrieval
def test_store_persists_and_retrieves(indexed, settings, embedder):
    assert indexed.store.count() > 0
    # reopen from disk: data must persist
    reopened = VectorStore(settings.chroma_dir, settings.collection_name,
                           embedder.model_name, embedder.dimension)
    assert reopened.count() == indexed.store.count()


@pytest.mark.parametrize("case", EVAL, ids=[c["question"][:40] for c in EVAL])
def test_eval_questions_retrieve_expected_page(indexed, case):
    result = indexed.retriever.retrieve(case["question"])
    assert result.chunks, "expected at least one relevant chunk"
    assert result.chunks[0].page_number == case["expected_page"]


def test_irrelevant_question_returns_nothing(indexed):
    result = indexed.retriever.retrieve("quantum chromodynamics lagrangian symmetry breaking")
    assert result.chunks == []
    assert result.dropped_for_distance > 0


def test_stale_versions_are_never_returned(indexed, policy_pdf):
    from .conftest import make_pdf

    new_pdf = make_pdf(["Eligibility\nStudents must hold a minimum CGPA of 8.0 for placements."])
    indexed.ingest_pdf(new_pdf, "policy.pdf", document_id="policy")
    result = indexed.retriever.retrieve("minimum CGPA eligibility")
    assert result.chunks
    assert {c.document_version for c in result.chunks} == {2}
    assert all("7.0" not in c.text for c in result.chunks)


def test_embedding_model_mismatch_is_rejected(indexed, settings):
    with pytest.raises(EmbeddingMismatchError):
        VectorStore(settings.chroma_dir, settings.collection_name, "other-model", 384)


def test_wrong_dimension_vectors_rejected(indexed):
    from src.chunking import Chunk

    chunk = Chunk("x", "d", "f.pdf", 1, 1, 0, "t")
    with pytest.raises(EmbeddingMismatchError):
        indexed.store.add_chunks([chunk], [[0.1, 0.2]])


def test_reranker_reorders_results(indexed, settings, embedder):
    def prefer_offer_page(query, passages):
        return [10.0 if "accepts a placement offer" in p else 0.0 for p in passages]

    rr = Retriever(indexed.store, embedder, indexed.registry, top_k=4, fetch_k=10,
                   max_distance=0.99, reranker=prefer_offer_page)
    result = rr.retrieve("placement offer eligibility CGPA")
    assert result.reranked is True
    assert result.chunks[0].page_number == 2


def test_empty_index_returns_no_chunks(pipeline):
    assert pipeline.retriever.retrieve("anything").chunks == []
