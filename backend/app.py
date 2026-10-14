"""FastAPI application for CampusCompass."""
from __future__ import annotations

import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from config import Settings, get_settings
from src.document_loader import PDFValidationError
from src.embeddings import SentenceTransformerEmbedder
from src.llm import ConfigurationError, LLMError, build_llm
from src.rag_pipeline import RAGPipeline
from src.retriever import Retriever, build_cross_encoder_reranker
from src.vector_store import DocumentRegistry, EmbeddingMismatchError, VectorStore
from src.web_search import TavilyWebSearch

log = logging.getLogger("campuscompass")


# ----------------------------------------------------------------- schemas
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, max_length=64)

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be blank")
        return v


class CitationModel(BaseModel):
    document_id: str
    filename: str
    document_version: int
    page_number: int
    chunk_id: str
    excerpt: str
    distance: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationModel]
    conversation_id: str
    grounded: bool
    retrieval: dict[str, Any]


class DocumentSummary(BaseModel):
    document_id: str
    version: int
    filename: str
    status: str
    is_current: bool
    page_count: int | None = None
    chunk_count: int | None = None
    uploaded_at: str
    updated_at: str


class DocumentDetail(DocumentSummary):
    content_hash: str
    pages_with_text: int | None = None
    error: str | None = None
    warnings: list[str] = []
    embedding_model: str | None = None


class DocumentsResponse(BaseModel):
    indexed_documents: int
    detailed: bool
    documents: list[DocumentSummary | DocumentDetail]


class UploadResponse(BaseModel):
    outcome: str  # "indexed" | "duplicate"
    message: str
    replaced_version: int | None = None
    document: DocumentDetail


class DeleteResponse(BaseModel):
    deleted: str


class HealthResponse(BaseModel):
    status: str
    components: dict[str, Any]


# ----------------------------------------------------------------- factory
def build_pipeline(settings: Settings) -> RAGPipeline:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    store = VectorStore(
        settings.chroma_dir, settings.collection_name, embedder.model_name, embedder.dimension
    )
    registry = DocumentRegistry(settings.registry_path)
    reranker = (
        build_cross_encoder_reranker(settings.rerank_model) if settings.enable_rerank else None
    )
    retriever = Retriever(
        store,
        embedder,
        registry,
        top_k=settings.top_k,
        fetch_k=settings.fetch_k,
        max_distance=settings.max_distance,
        reranker=reranker,
    )
    llm = build_llm(
        provider=settings.llm_provider,
        model=settings.llm_model,
        ollama_base_url=settings.ollama_base_url,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
    )
    web_search = (
        TavilyWebSearch(
            settings.tavily_api_key,
            max_results=settings.web_search_max_results,
            timeout=settings.web_search_timeout_seconds,
        )
        if settings.web_search_enabled and settings.tavily_api_key
        else None
    )
    return RAGPipeline(
        store=store,
        registry=registry,
        embedder=embedder,
        retriever=retriever,
        llm=llm,
        web_search=web_search,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def create_app(
    settings: Settings | None = None, pipeline: RAGPipeline | None = None
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.init_error = None
        if pipeline is not None:
            app.state.pipeline = pipeline
        else:
            try:
                app.state.pipeline = build_pipeline(settings)
            except (EmbeddingMismatchError, ConfigurationError) as exc:
                log.error("Startup failed: %s", exc)
                app.state.pipeline = None
                app.state.init_error = str(exc)
        yield

    app = FastAPI(title="CampusCompass API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def get_pipeline() -> RAGPipeline:
        p = getattr(app.state, "pipeline", None)
        if p is None:
            raise HTTPException(503, detail=app.state.init_error or "Service is not ready.")
        return p

    def optional_admin(authorization: str | None = Header(default=None)) -> bool:
        return _is_admin(authorization, settings)

    def require_admin(authorization: str | None = Header(default=None)) -> None:
        if not settings.admin_token:
            raise HTTPException(503, detail="Administration is disabled: ADMIN_API_TOKEN is not set.")
        if not _is_admin(authorization, settings):
            raise HTTPException(
                401, detail="Administrator authorization required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # ------------------------------------------------------------- health
    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        p = getattr(app.state, "pipeline", None)
        components: dict[str, Any] = {
            "admin_configured": bool(settings.admin_token),
            "embedding_model": settings.embedding_model,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "web_search": {
                "enabled": settings.web_search_enabled,
                "configured": bool(settings.tavily_api_key),
            },
        }
        if p is None:
            components["vector_store"] = {"ok": False, "error": app.state.init_error}
            return HealthResponse(status="degraded", components=components)
        try:
            components["vector_store"] = {"ok": True, "chunks": p.store.count()}
        except Exception:
            components["vector_store"] = {"ok": False}
        llm_ok = p.llm.is_available()
        components["llm"] = {"ok": llm_ok}
        components["indexed_documents"] = p.registry.ready_count()
        ok = components["vector_store"]["ok"] and llm_ok
        return HealthResponse(status="ok" if ok else "degraded", components=components)

    # ---------------------------------------------------------- documents
    @app.get("/documents", response_model=DocumentsResponse)
    def list_documents(
        is_admin: bool = Depends(optional_admin), p: RAGPipeline = Depends(get_pipeline)
    ) -> DocumentsResponse:
        records = p.registry.list(include_archived=is_admin)
        if is_admin:
            docs: list[DocumentSummary | DocumentDetail] = [
                DocumentDetail(**r.to_dict()) for r in records
            ]
        else:
            docs = [
                DocumentSummary(**{k: v for k, v in r.to_dict().items() if k in DocumentSummary.model_fields})
                for r in records
                if r.status == "ready" and r.is_current
            ]
        return DocumentsResponse(
            indexed_documents=p.registry.ready_count(), detailed=is_admin, documents=docs
        )

    @app.post("/documents/upload", response_model=UploadResponse, dependencies=[Depends(require_admin)])
    def upload_document(
        file: UploadFile = File(...),
        document_id: str | None = Form(default=None, max_length=80),
        p: RAGPipeline = Depends(get_pipeline),
    ) -> UploadResponse:
        name = file.filename or ""
        if not name.lower().endswith(".pdf"):
            raise HTTPException(400, detail="Only .pdf files are accepted.")
        data = _read_limited(file, settings.max_upload_bytes)
        try:
            result = p.ingest_pdf(data, name, document_id)
        except PDFValidationError as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        except EmbeddingMismatchError as exc:
            raise HTTPException(409, detail=str(exc)) from exc
        except Exception as exc:
            log.exception("Indexing failed")
            raise HTTPException(500, detail=f"Indexing failed: {exc}") from exc

        if result.outcome == "duplicate":
            message = (
                f"Identical content is already indexed as '{result.record.document_id}' "
                f"v{result.record.version}; nothing was changed."
            )
        elif result.replaced_version is not None:
            message = (
                f"Indexed as v{result.record.version}; version {result.replaced_version} "
                "was archived and removed from search."
            )
        else:
            message = f"Indexed as '{result.record.document_id}' v{result.record.version}."
        return UploadResponse(
            outcome=result.outcome,
            message=message,
            replaced_version=result.replaced_version,
            document=DocumentDetail(**result.record.to_dict()),
        )

    @app.delete(
        "/documents/{document_id}",
        response_model=DeleteResponse,
        dependencies=[Depends(require_admin)],
    )
    def delete_document(
        document_id: str,
        confirm: str | None = Query(default=None, description="Must equal the document_id."),
        p: RAGPipeline = Depends(get_pipeline),
    ) -> DeleteResponse:
        if confirm != document_id:
            raise HTTPException(
                400, detail="Deletion not confirmed. Pass ?confirm=<document_id> to proceed."
            )
        if not p.delete_document(document_id):
            raise HTTPException(404, detail="Document not found.")
        return DeleteResponse(deleted=document_id)

    # --------------------------------------------------------------- chat
    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest, p: RAGPipeline = Depends(get_pipeline)) -> ChatResponse:
        try:
            result = p.answer(req.question, req.conversation_id)
        except LLMError as exc:
            log.warning("LLM error: %s", exc)
            raise HTTPException(
                503,
                detail="The language model is temporarily unavailable. Please try again shortly.",
            ) from exc
        return ChatResponse(
            answer=result.answer,
            citations=[CitationModel(**c.__dict__) for c in result.citations],
            conversation_id=result.conversation_id,
            grounded=result.grounded,
            retrieval=result.retrieval,
        )

    return app


# ----------------------------------------------------------------- helpers
def _is_admin(authorization: str | None, settings: Settings) -> bool:
    if not settings.admin_token or not authorization:
        return False
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return False
    return hmac.compare_digest(token.strip().encode(), settings.admin_token.encode())


def _read_limited(file: UploadFile, limit: int) -> bytes:
    buf = bytearray()
    while True:
        part = file.file.read(1024 * 1024)
        if not part:
            break
        buf.extend(part)
        if len(buf) > limit:
            raise HTTPException(
                413, detail=f"File exceeds the {limit // (1024 * 1024)} MB upload limit."
            )
    return bytes(buf)


app = create_app()
