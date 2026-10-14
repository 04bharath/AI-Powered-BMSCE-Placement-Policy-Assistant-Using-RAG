"""PDF loading with page-accurate text extraction and validation."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz  # PyMuPDF


class PDFValidationError(ValueError):
    """Raised when an uploaded file is not a usable PDF."""


@dataclass(frozen=True)
class PageText:
    page_number: int  # 1-based, the actual PDF page index
    text: str


@dataclass
class LoadedDocument:
    filename: str
    content_hash: str
    page_count: int
    pages: list[PageText] = field(default_factory=list)  # only pages with text
    empty_pages: list[int] = field(default_factory=list)  # pages with no extractable text


_WS_RE = re.compile(r"[ \t ]+")
_BLANKS_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise whitespace without altering the policy wording."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    text = _WS_RE.sub(" ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    return _BLANKS_RE.sub("\n\n", text).strip()


def sanitize_filename(name: str) -> str:
    """Keep only the base name and safe characters."""
    base = Path(name or "").name
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return base or "document.pdf"


def load_pdf_bytes(data: bytes, filename: str) -> LoadedDocument:
    """Extract text page by page from raw PDF bytes.

    Raises PDFValidationError for empty, non-PDF, corrupt, encrypted or
    text-less (e.g. scanned, image-only) files.
    """
    if not data:
        raise PDFValidationError("The uploaded file is empty.")
    if not data.lstrip()[:5] == b"%PDF-":
        raise PDFValidationError("The file content is not a PDF (missing %PDF header).")

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # fitz raises several error types
        raise PDFValidationError(f"The PDF could not be opened: {exc}") from exc

    try:
        if doc.needs_pass:
            raise PDFValidationError("Password-protected PDFs are not supported.")
        if doc.page_count == 0:
            raise PDFValidationError("The PDF contains no pages.")

        pages: list[PageText] = []
        empty: list[int] = []
        for index in range(doc.page_count):
            try:
                raw = doc.load_page(index).get_text("text")
            except Exception as exc:
                raise PDFValidationError(
                    f"Failed to read text from page {index + 1}: {exc}"
                ) from exc
            text = clean_text(raw)
            if text:
                pages.append(PageText(page_number=index + 1, text=text))
            else:
                empty.append(index + 1)
        page_count = doc.page_count
    finally:
        doc.close()

    if not pages:
        raise PDFValidationError(
            "No extractable text found. The PDF may be scanned images; OCR is not supported yet."
        )

    return LoadedDocument(
        filename=sanitize_filename(filename),
        content_hash=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
        pages=pages,
        empty_pages=empty,
    )


def load_pdf_path(path: str | Path) -> LoadedDocument:
    p = Path(path)
    return load_pdf_bytes(p.read_bytes(), p.name)
