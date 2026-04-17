"""
RAG tuning: profile presets and effective env resolution.

RAG_PROFILE=fast — lower retrieval count and tighter prompt excerpts (cost/latency).
Explicit RAG_TOP_K / RAG_MAX_* always win when set.
"""

from __future__ import annotations

import os


def _profile() -> str:
    return (os.getenv("RAG_PROFILE") or "").strip().lower()


def effective_rag_top_k() -> int:
    """Chunks to retrieve; fast default 2, otherwise 3."""
    raw = os.getenv("RAG_TOP_K")
    if raw is not None and str(raw).strip() != "":
        return max(1, int(str(raw).strip()))
    return 2 if _profile() == "fast" else 3


def effective_max_chunks_in_prompt() -> int:
    """Max chunks passed to the LLM after retrieval; fast default 2."""
    raw = os.getenv("RAG_MAX_CHUNKS_IN_PROMPT")
    if raw is not None and str(raw).strip() != "":
        return max(1, int(str(raw).strip()))
    return 2 if _profile() == "fast" else 3


def effective_max_chars_per_chunk() -> int:
    """Per-chunk excerpt cap in the grounding message; fast default 700."""
    raw = os.getenv("RAG_MAX_CHARS_PER_CHUNK")
    if raw is not None and str(raw).strip() != "":
        return max(300, int(str(raw).strip()))
    return 700 if _profile() == "fast" else 1200


def effective_vector_n_candidates(k: int) -> int:
    """Chroma candidate pool size; smaller in fast mode for lower latency."""
    k = max(1, k)
    if _profile() == "fast":
        return max(k * 2, 6)
    return max(k * 3, 8)
