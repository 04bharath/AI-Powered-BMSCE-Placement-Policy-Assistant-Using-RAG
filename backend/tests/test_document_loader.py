import pytest

from src.document_loader import PDFValidationError, load_pdf_bytes, sanitize_filename

from .conftest import make_pdf


def test_extracts_text_page_by_page(policy_pdf):
    doc = load_pdf_bytes(policy_pdf, "policy.pdf")
    assert doc.page_count == 3
    assert [p.page_number for p in doc.pages] == [1, 2, 3]
    assert "minimum CGPA of 7.0" in doc.pages[0].text
    assert "accepts a placement offer" in doc.pages[1].text
    assert "Internship offers" in doc.pages[2].text


def test_page_numbers_preserved_when_a_page_is_blank():
    pdf = make_pdf(["Page one text here.", "ignored", "Page three text here."], blank_pages={2})
    doc = load_pdf_bytes(pdf, "gap.pdf")
    assert [p.page_number for p in doc.pages] == [1, 3]
    assert doc.empty_pages == [2]
    assert doc.page_count == 3


def test_hash_is_stable_and_content_sensitive(policy_pdf):
    a = load_pdf_bytes(policy_pdf, "a.pdf")
    b = load_pdf_bytes(policy_pdf, "b.pdf")
    c = load_pdf_bytes(make_pdf(["different"]), "c.pdf")
    assert a.content_hash == b.content_hash != c.content_hash


@pytest.mark.parametrize(
    "payload, fragment",
    [
        (b"", "empty"),
        (b"just some text, not a pdf", "not a PDF"),
        (b"%PDF-1.7\nthis is garbage and not a real pdf body", "could not be opened"),
    ],
)
def test_rejects_empty_and_malformed(payload, fragment):
    with pytest.raises(PDFValidationError) as exc:
        load_pdf_bytes(payload, "x.pdf")
    assert fragment.lower() in str(exc.value).lower()


def test_rejects_pdf_without_extractable_text():
    with pytest.raises(PDFValidationError, match="No extractable text"):
        load_pdf_bytes(make_pdf(["", ""], blank_pages={1, 2}), "scan.pdf")


def test_sanitize_filename_strips_paths():
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename("my policy (v2).pdf") == "my policy _v2_.pdf"
