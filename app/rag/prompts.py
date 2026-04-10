"""
System text for RAG-grounded generation. Deterministic; no LLM calls.
"""

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


def format_rag_message(chunks: list[dict]) -> str:
    """Build a single system message string from ranked chunk dicts."""
    if not chunks:
        return ""

    lines = [RAG_GROUNDING_HEADER, ""]
    for i, ch in enumerate(chunks, start=1):
        src = ch.get("source", "unknown")
        topic = ch.get("topic", "")
        heading = ch.get("heading", "")
        meta = f"[{i}] source={src}"
        if topic:
            meta += f" topic={topic}"
        if heading:
            meta += f" section={heading!r}"
        lines.append(meta)
        lines.append(ch.get("text", "").strip())
        lines.append("")

    lines.append(FOOTER)
    return "\n".join(lines).strip()
