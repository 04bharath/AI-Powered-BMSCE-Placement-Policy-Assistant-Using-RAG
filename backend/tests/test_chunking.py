import pytest

from src.chunking import chunk_pages
from src.document_loader import PageText

LONG = " ".join(f"Sentence number {i} describes a placement rule." for i in range(60))


def _chunks(pages, size=300, overlap=50):
    return chunk_pages(pages, document_id="doc", filename="p.pdf", document_version=1,
                       chunk_size=size, chunk_overlap=overlap)


def test_chunks_respect_size_limit():
    chunks = _chunks([PageText(1, LONG)])
    assert len(chunks) > 3
    assert all(len(c.text) <= 300 for c in chunks)


def test_overlap_between_consecutive_chunks():
    chunks = _chunks([PageText(1, LONG)])
    shared = 0
    for a, b in zip(chunks, chunks[1:]):
        tail_words = set(a.text.split()[-4:])
        if tail_words & set(b.text.split()[:12]):
            shared += 1
    assert shared >= len(chunks) - 2  # nearly every boundary overlaps


def test_chunks_never_cross_pages_and_keep_page_numbers():
    pages = [PageText(2, LONG), PageText(5, "Short page five text.")]
    chunks = _chunks(pages)
    assert {c.page_number for c in chunks} == {2, 5}
    page5 = [c for c in chunks if c.page_number == 5]
    assert len(page5) == 1 and page5[0].text == "Short page five text."
    assert all("page five" not in c.text for c in chunks if c.page_number == 2)


def test_metadata_and_unique_ids():
    chunks = _chunks([PageText(1, LONG), PageText(2, LONG)])
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    meta = chunks[0].metadata()
    assert meta["document_id"] == "doc" and meta["filename"] == "p.pdf"
    assert meta["document_version"] == 1 and meta["page_number"] == 1


@pytest.mark.parametrize("size, overlap", [(0, 0), (100, 100), (100, 150), (100, -1)])
def test_invalid_parameters_rejected(size, overlap):
    with pytest.raises(ValueError):
        _chunks([PageText(1, "text")], size, overlap)
