import logging
import json
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.rag import embeddings, store
from app.rag.knowledge import MODEL, chunk_text
from app.rag.processing import extract_text, normalize_text
from app.rag.context import assemble_context

router = APIRouter(prefix="/internal/v1/knowledge", tags=["knowledge"])
logger = logging.getLogger(__name__)


class DocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=500)
    text: str | None = Field(default=None, min_length=1, max_length=20000)
    filename: str | None = Field(default=None, min_length=1, max_length=255)
    contentBase64: str | None = Field(default=None, max_length=2666668)
    metadata: dict[str, str] = Field(default_factory=dict)
    chunkSize: int = Field(default=350, ge=50, le=1500)
    chunkOverlap: int = Field(default=60, ge=0)

    @model_validator(mode="after")
    def validate_document(self):
        if (self.text is None) == (self.contentBase64 is None):
            raise ValueError("Provide exactly one of text or contentBase64")
        if self.contentBase64 is not None and not self.filename:
            raise ValueError("Filename is required for file ingestion")
        if self.chunkOverlap >= self.chunkSize:
            raise ValueError("Chunk overlap must be smaller than chunk size")
        if len(self.metadata) > 20 or len(json.dumps(self.metadata)) > 4000:
            raise ValueError("Metadata exceeds bounds")
        return self

    @field_validator("title", "source", "text")
    @classmethod
    def strip_nonempty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    top_k: int | None = Field(default=None, ge=1, le=20)
    minScore: float = Field(default=0.0, ge=-1.0, le=1.0, allow_inf_nan=False)
    metadataFilter: dict[str, str] = Field(default_factory=dict)
    maxContextChars: int = Field(default=6000, ge=200, le=12000)

    @field_validator("metadataFilter")
    @classmethod
    def bounded_filter(cls, value):
        if len(value) > 20 or len(json.dumps(value)) > 4000:
            raise ValueError("Metadata filter exceeds bounds")
        return value

    @field_validator("query")
    @classmethod
    def nonempty_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()


class DocumentResponse(BaseModel):
    documentId: str
    chunks: int
    deduplicated: bool
    model: str
    status: str = "indexed"
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchHit(BaseModel):
    chunkId: str
    documentId: str
    title: str
    source: str
    ordinal: int
    content: str
    score: float
    metadata: dict[str, str] = Field(default_factory=dict)
    filename: str | None = None


class ContextReference(BaseModel):
    reference: str
    documentId: str
    chunkId: str
    title: str
    source: str
    score: float


class RetrievalContext(BaseModel):
    status: str
    text: str
    references: list[ContextReference]
    generatedAnswer: str | None = None


class SearchResponse(BaseModel):
    model: str
    dimensions: int = 384
    results: list[SearchHit]
    context: RetrievalContext


def unavailable(error: Exception):
    logger.warning("Knowledge operation unavailable", extra={"error_type": type(error).__name__})
    raise HTTPException(status_code=503, detail="Knowledge service unavailable; check database and embedding model") from error


@router.post("/documents", response_model=DocumentResponse, status_code=201)
def ingest_document(request: DocumentRequest):
    try:
        text = normalize_text(request.text) if request.text is not None else extract_text(request.filename, request.contentBase64)
        chunks = chunk_text(text, request.chunkSize, request.chunkOverlap)
        vectors = embeddings.embed(chunks)
        return store.save_document(request.title, request.source, text, chunks, vectors,
                                   request.metadata, request.filename, request.chunkSize, request.chunkOverlap)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (psycopg.Error, store.KnowledgeUnavailable, OSError, RuntimeError) as error:
        unavailable(error)


@router.post("/search", response_model=SearchResponse)
def semantic_search(request: SearchRequest):
    try:
        vector = embeddings.embed([request.query])[0]
        hits = store.search(vector, request.top_k or request.limit, request.minScore, request.metadataFilter)
        return {"model": MODEL, "results": hits, "context": assemble_context(hits, request.maxContextChars)}
    except (psycopg.Error, store.KnowledgeUnavailable, OSError, RuntimeError, ValueError) as error:
        unavailable(error)


class DocumentDetails(BaseModel):
    documentId: str
    title: str
    source: str
    filename: str | None
    metadata: dict[str, str]
    contentHash: str
    model: str
    chunks: int
    chunkSize: int
    chunkOverlap: int
    createdAt: str
    updatedAt: str


@router.get("/documents", response_model=list[DocumentDetails])
def list_documents(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0, le=100000)):
    try:
        return store.list_documents(limit, offset)
    except (psycopg.Error, store.KnowledgeUnavailable) as error:
        unavailable(error)


@router.get("/documents/{document_id}", response_model=DocumentDetails)
def get_document(document_id: UUID):
    try:
        document = store.get_document(str(document_id))
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except (psycopg.Error, store.KnowledgeUnavailable) as error:
        unavailable(error)
