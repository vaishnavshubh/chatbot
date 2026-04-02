"""
Build data/rag_index/chunks.jsonl from Markdown files in data/rag/.

Run from project root:
    python app/rag/ingest.py

Topic is inferred from filename: e.g. credit_management.md -> topic \"credit_management\".
Each ## section becomes one chunk.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s[:48] or "section"


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Return list of (heading, body) for each ## section."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = "introduction"
    buf: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if buf:
                sections.append((current_heading, buf))
            current_heading = line[3:].strip()
            buf = []
        else:
            buf.append(line)

    if buf:
        sections.append((current_heading, buf))

    return [(h, "\n".join(b).strip()) for h, b in sections if "\n".join(b).strip()]


def ingest(rag_dir: Path, out_path: Path) -> int:
    md_files = sorted(rag_dir.glob("*.md"))
    # Skip README
    md_files = [p for p in md_files if p.name.lower() != "readme.md"]

    rows: list[dict] = []
    for path in md_files:
        stem = path.stem
        if stem.startswith("topic_"):
            topic = stem[len("topic_") :]
        else:
            topic = stem

        text = path.read_text(encoding="utf-8")
        # Drop a single top-level # title if present (not chunked separately)
        text = re.sub(r"^#\s+[^\n]+\n+", "", text, count=1, flags=re.MULTILINE)

        for idx, (heading, body) in enumerate(_split_sections(text)):
            cid = f"{topic}_{_slug(heading)}_{idx}"
            rows.append(
                {
                    "id": cid,
                    "text": body,
                    "source": path.name,
                    "topic": topic,
                    "heading": heading,
                }
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows)


def main() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    rag_dir = root / "data" / "rag"
    out = root / "data" / "rag_index" / "chunks.jsonl"

    ap = argparse.ArgumentParser(description="Build RAG chunks.jsonl from data/rag/*.md")
    ap.add_argument("--rag-dir", type=Path, default=rag_dir)
    ap.add_argument("--out", type=Path, default=out)
    args = ap.parse_args()

    n = ingest(args.rag_dir, args.out)
    print(f"Wrote {n} chunks to {args.out}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
