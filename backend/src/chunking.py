"""Page-aware chunking that never merges text across pages."""
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .document_loader import PageText


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    filename: str
    document_version: int
    page_number: int
    chunk_index: int
    text: str

    def metadata(self) -> dict[str, str | int]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "document_version": self.document_version,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "chunk_id": self.chunk_id,
        }


def chunk_pages(
    pages: list[PageText],
    *,
    document_id: str,
    filename: str,
    document_version: int,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    """Split each page independently so every chunk maps to exactly one real PDF page."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )

    chunks: list[Chunk] = []
    for page in pages:
        for idx, piece in enumerate(splitter.split_text(page.text)):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}:v{document_version}:p{page.page_number}:c{idx}",
                    document_id=document_id,
                    filename=filename,
                    document_version=document_version,
                    page_number=page.page_number,
                    chunk_index=idx,
                    text=piece,
                )
            )
    return chunks
