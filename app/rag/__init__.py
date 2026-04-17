"""RAG: load chunks, retrieve by keywords, format context for the Speaker."""

from __future__ import annotations

from typing import Any

from rag.prompts import format_rag_message
from rag.retrieval import RAGRetriever

__all__ = ["RAGRetriever", "RAGVectorRetriever", "format_rag_message"]


def __getattr__(name: str) -> Any:
    """Lazy import so JSONL-only deployments never load chromadb/protobuf stack."""
    if name == "RAGVectorRetriever":
        from rag.retrieval_vector import RAGVectorRetriever

        return RAGVectorRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
