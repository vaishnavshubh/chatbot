"""
System text for RAG-grounded generation. Deterministic; no LLM calls.
"""

from rag.rag_settings import (
    effective_max_chars_per_chunk,
    effective_max_chunks_in_prompt,
)

RAG_GROUNDING_HEADER = """RETRIEVED EXCERPTS (curated knowledge base)

The following excerpts were retrieved automatically based on the user's selected topic.
They are for educational grounding only. They may be incomplete.

Rules you MUST follow:
- Prefer explaining concepts using ideas supported by these excerpts when relevant.
- If the excerpts do not cover a detail, say the knowledge base does not specify it rather than inventing specifics.
- Never recommend specific financial products, institutions, funds, or credit cards by name.
- This remains educational information, not personalized financial advice.
"""

FOOTER = (
    "\n---\nEnd of retrieved excerpts. Continue following your Speaker skill and "
    "orchestrator instruction for structure and tone."
)


def _truncate_excerpt(text: str, max_chars: int) -> str:
    clean = (text or "").strip()
    if len(clean) <= max_chars:
        return clean
    # Keep prompts compact to reduce token cost/latency.
    return clean[: max_chars - 15].rstrip() + "\n...[truncated]"


def format_rag_message(chunks: list[dict]) -> str:
    """Build a single system message string from ranked chunk dicts."""
    if not chunks:
        return ""

    max_chunks = effective_max_chunks_in_prompt()
    max_chars = effective_max_chars_per_chunk()

    lines = [RAG_GROUNDING_HEADER, ""]
    for i, ch in enumerate(chunks[:max_chunks], start=1):
        src = ch.get("source_document") or ch.get("source", "unknown")
        topic = ch.get("topic", "")
        heading = ch.get("parent_section") or ch.get("heading", "")
        page_number = ch.get("page_number")
        chunk_type = ch.get("chunk_type", "")
        meta = f"[{i}] source={src}"
        if isinstance(page_number, int):
            meta += f" page={page_number}"
        if topic:
            meta += f" topic={topic}"
        if heading:
            meta += f" section={heading!r}"
        if chunk_type:
            meta += f" type={chunk_type}"
        lines.append(meta)
        lines.append(_truncate_excerpt(ch.get("text", ""), max_chars=max_chars))
        lines.append("")

    lines.append(FOOTER)
    return "\n".join(lines).strip()
