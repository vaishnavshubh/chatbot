"""
Vector retrieval for legal/tax RAG chunks stored in Chroma.

Implements the same public contract as RAGRetriever:
- enabled property
- retrieve_for_state(state, k)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import chromadb

from rag.rag_settings import effective_vector_n_candidates
from rag.retrieval import GOAL_KEYWORDS

log = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _keyword_score(query_tokens: set[str], chunk: dict[str, Any]) -> float:
    text = (chunk.get("text") or "") + " " + (chunk.get("heading") or "")
    doc_tokens = _tokenize(text)
    if not doc_tokens or not query_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / max(1, len(query_tokens))


class RAGVectorRetriever:
    def __init__(self, persist_dir: Path | None, collection_name: str = "finlit_hard_rules"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._collection = None
        self._enabled = False
        if not persist_dir:
            return
        if not persist_dir.exists():
            log.warning("RAG vector directory not found: %s", persist_dir)
            return
        try:
            client = chromadb.PersistentClient(path=str(persist_dir))
            self._collection = client.get_collection(name=collection_name)
            self._enabled = self._collection.count() > 0
            log.info(
                "Loaded vector collection '%s' with %d chunks",
                collection_name,
                self._collection.count(),
            )
        except Exception as exc:
            log.warning("Could not initialize vector retriever: %s", exc)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def build_query(self, primary_goal: str | None) -> str:
        g = primary_goal or "financial_foundations"
        extra = GOAL_KEYWORDS.get(g, "")
        return f"{g.replace('_', ' ')} {extra} legal tax retirement plan rules requirements"

    def retrieve(self, query: str, k: int = 5, topic_filter: str | None = None) -> list[dict]:
        if not self._collection:
            return []
        n_results = effective_vector_n_candidates(k)
        where = {"topic": topic_filter} if topic_filter else None

        try:
            res = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances", "ids"],
            )
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            ids = res.get("ids", [[]])[0]
        except Exception as exc:
            log.warning("Vector query failed: %s", exc)
            return []

        if not docs:
            return []

        query_tokens = _tokenize(query)
        scored: list[tuple[float, dict]] = []
        for idx, doc in enumerate(docs):
            meta = metas[idx] or {}
            dist = float(dists[idx]) if idx < len(dists) else 1.0
            cid = ids[idx] if idx < len(ids) else f"vector_{idx}"
            row = {
                "id": cid,
                "text": doc or "",
                "source": meta.get("source", meta.get("source_document", "unknown")),
                "topic": meta.get("topic", ""),
                "heading": meta.get("heading", meta.get("parent_section", "")),
                "source_document": meta.get("source_document", ""),
                "page_number": meta.get("page_number"),
                "parent_section": meta.get("parent_section", ""),
                "chunk_type": meta.get("chunk_type", "text"),
                "document_group": meta.get("document_group", ""),
            }
            vector_sim = 1.0 / (1.0 + max(0.0, dist))
            keyword_sim = _keyword_score(query_tokens, row)
            topic_bonus = 0.2 if topic_filter and row.get("topic") == topic_filter else 0.0
            score = 0.7 * vector_sim + 0.3 * keyword_sim + topic_bonus
            scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        out: list[dict] = []
        seen: set[str] = set()
        for _, row in scored:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            out.append(row)
            if len(out) >= k:
                break
        return out

    def retrieve_for_state(self, state: Any, k: int = 5) -> list[dict]:
        goal = getattr(getattr(state, "goal", None), "primary_goal", None)
        query = self.build_query(goal)
        return self.retrieve(query, k=k, topic_filter=goal)
