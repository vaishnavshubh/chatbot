"""
Hierarchical PDF ingestion for legal/tax documents into a vector store.

Default input documents (under data/rag_pdfs/):
  - IRS Publication 560.pdf
  - IRS Publication 575.pdf
  - IRS Publication 590b.pdf
  - US Code Title 26 Section 401.pdf

Outputs:
  - Normalized chunk audit JSONL
  - Persistent Chroma vector collection
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
import pdfplumber

log = logging.getLogger(__name__)

DEFAULT_PDFS = [
    "IRS Publication 560.pdf",
    "IRS Publication 575.pdf",
    "IRS Publication 590b.pdf",
    "US Code Title 26 Section 401.pdf",
]


DOC_CONFIG: dict[str, dict[str, str]] = {
    "irs publication 560.pdf": {
        "source_document": "IRS Pub 560",
        "document_group": "irs_publication",
        "topic": "workplace_401k",
    },
    "irs publication 575.pdf": {
        "source_document": "IRS Pub 575",
        "document_group": "irs_publication",
        "topic": "workplace_401k",
    },
    "irs publication 590b.pdf": {
        "source_document": "IRS Pub 590-B",
        "document_group": "irs_publication",
        "topic": "workplace_401k",
    },
    "us code title 26 section 401.pdf": {
        "source_document": "26 U.S.C. §401",
        "document_group": "us_code",
        "topic": "workplace_401k",
    },
}

_TABLE_TAG = "[[TABLE_"


@dataclass
class Block:
    text: str
    block_type: str  # text | list | table | callout
    page_number: int


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:80] or "chunk"


def _token_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _tail_tokens(text: str, n: int) -> str:
    toks = re.findall(r"\S+", text)
    if not toks:
        return ""
    return " ".join(toks[-n:])


def _looks_multicolumn(words: list[dict[str, Any]], page_width: float) -> bool:
    if len(words) < 25:
        return False
    centers = [((w["x0"] + w["x1"]) / 2.0) for w in words if "x0" in w and "x1" in w]
    if len(centers) < 10:
        return False
    med = statistics.median(centers)
    left = sum(1 for c in centers if c < med)
    right = sum(1 for c in centers if c >= med)
    balance = min(left, right) / max(1, max(left, right))
    mid = page_width / 2.0
    return balance > 0.35 and abs(med - mid) < page_width * 0.12


def _words_to_lines(words: list[dict[str, Any]], y_tol: float = 3.0) -> list[str]:
    if not words:
        return []
    ws = sorted(words, key=lambda w: (round(float(w.get("top", 0.0)) / y_tol), float(w.get("x0", 0.0))))
    lines: list[list[str]] = []
    ys: list[float] = []
    for w in ws:
        top = float(w.get("top", 0.0))
        txt = str(w.get("text", "")).strip()
        if not txt:
            continue
        if not lines:
            lines.append([txt])
            ys.append(top)
            continue
        if abs(top - ys[-1]) <= y_tol:
            lines[-1].append(txt)
        else:
            lines.append([txt])
            ys.append(top)
    return [" ".join(parts).strip() for parts in lines if parts]


def _extract_page_text(page: pdfplumber.page.Page) -> str:
    words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
    if not words:
        return page.extract_text() or ""

    if _looks_multicolumn(words, float(page.width)):
        split_x = float(page.width) / 2.0
        left = [w for w in words if float(w.get("x0", 0.0)) < split_x]
        right = [w for w in words if float(w.get("x0", 0.0)) >= split_x]
        left_lines = _words_to_lines(left)
        right_lines = _words_to_lines(right)
        lines = left_lines + right_lines
    else:
        lines = _words_to_lines(words)
    return "\n".join(lines).strip()


def _table_to_markdown(table: list[list[str | None]]) -> str:
    rows = [[(c or "").strip().replace("\n", " ") for c in row] for row in table if row]
    rows = [r for r in rows if any(cell for cell in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    normalized = [r + [""] * (width - len(r)) for r in rows]
    header = normalized[0]
    sep = ["---"] * width
    body = normalized[1:] if len(normalized) > 1 else []
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    out.extend("| " + " | ".join(r) + " |" for r in body)
    return "\n".join(out)


def _extract_page_tables(page: pdfplumber.page.Page, page_number: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for idx, table in enumerate(page.extract_tables() or []):
        md = _table_to_markdown(table)
        if not md:
            continue
        placeholder = f"{_TABLE_TAG}{page_number}_{idx}]]"
        out.append((placeholder, md))
    return out


def _normalize_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def _is_heading_irs(line: str) -> bool:
    if re.match(r"^chapter\s+\d+\b", line, flags=re.IGNORECASE):
        return True
    if re.match(r"^\d+(\.\d+)*\s+[A-Z].+", line):
        return True
    if line.isupper() and 6 <= len(line) <= 120:
        return True
    return False


def _is_callout(line: str) -> bool:
    return bool(re.match(r"^(caution|reminder|warning|tip)\b[:\-]?", line, flags=re.IGNORECASE))


def _is_list_line(line: str) -> bool:
    return bool(re.match(r"^([-\u2022*]|\d+[\.\)]|[A-Za-z][\.\)])\s+", line))


def _irs_blocks_from_text(text: str, page_number: int) -> list[Block]:
    lines = _normalize_lines(text)
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith(_TABLE_TAG):
            blocks.append(Block(text=ln, block_type="table", page_number=page_number))
            i += 1
            continue
        if _is_callout(ln):
            buf = [ln]
            i += 1
            while i < len(lines) and not (_is_heading_irs(lines[i]) or lines[i].startswith(_TABLE_TAG)):
                if _is_callout(lines[i]):
                    break
                buf.append(lines[i])
                i += 1
            blocks.append(Block(text="\n".join(buf), block_type="callout", page_number=page_number))
            continue
        if _is_list_line(ln):
            buf = [ln]
            i += 1
            while i < len(lines) and (_is_list_line(lines[i]) or lines[i].startswith(("(", "See ", "Note " ))):
                if lines[i].startswith(_TABLE_TAG):
                    break
                buf.append(lines[i])
                i += 1
            blocks.append(Block(text="\n".join(buf), block_type="list", page_number=page_number))
            continue
        blocks.append(Block(text=ln, block_type="text", page_number=page_number))
        i += 1
    return blocks


def _usc_path_for_line(line: str, stack: dict[str, str]) -> tuple[str, dict[str, str]]:
    sec = re.search(r"§\s*401\b", line)
    subsec = re.match(r"^\(([a-z])\)", line)
    para = re.match(r"^\((\d+)\)", line)
    subpara = re.match(r"^\(([A-Z])\)", line)
    clause = re.match(r"^\(([ivxlcdm]+)\)", line, flags=re.IGNORECASE)

    updated = dict(stack)
    if sec:
        updated["section"] = "§401"
    if subsec:
        updated["subsection"] = f"({subsec.group(1)})"
        updated.pop("paragraph", None)
        updated.pop("subparagraph", None)
        updated.pop("clause", None)
    elif para:
        updated["paragraph"] = f"({para.group(1)})"
        updated.pop("subparagraph", None)
        updated.pop("clause", None)
    elif subpara:
        updated["subparagraph"] = f"({subpara.group(1)})"
        updated.pop("clause", None)
    elif clause:
        updated["clause"] = f"({clause.group(1).lower()})"

    path = " > ".join(v for _, v in sorted(updated.items(), key=lambda kv: ["section", "subsection", "paragraph", "subparagraph", "clause"].index(kv[0])))
    return path or "§401", updated


def _usc_blocks_from_text(text: str, page_number: int) -> list[Block]:
    lines = _normalize_lines(text)
    blocks: list[Block] = []
    buf: list[str] = []
    for ln in lines:
        if ln.startswith(_TABLE_TAG):
            if buf:
                blocks.append(Block(text="\n".join(buf), block_type="text", page_number=page_number))
                buf = []
            blocks.append(Block(text=ln, block_type="table", page_number=page_number))
            continue
        if re.match(r"^\([a-zA-Z0-9ivxlcdmIVXLCDM]+\)\s+", ln) and buf:
            blocks.append(Block(text="\n".join(buf), block_type="text", page_number=page_number))
            buf = [ln]
        else:
            buf.append(ln)
    if buf:
        blocks.append(Block(text="\n".join(buf), block_type="text", page_number=page_number))
    return blocks


def _restore_table_placeholders(text: str, table_map: dict[str, str]) -> tuple[str, str]:
    content = text
    chunk_type = "text"
    for key, md in table_map.items():
        if key in content:
            content = content.replace(key, md)
            chunk_type = "table"
    return content, chunk_type


def _append_overlap(chunks: list[dict], overlap_ratio: float = 0.12) -> list[dict]:
    out: list[dict] = []
    prev_by_section: dict[tuple[str, str], str] = {}
    for ch in chunks:
        section_key = (ch.get("source_document", ""), ch.get("parent_section", ""))
        content = ch["text"]
        if ch.get("chunk_type") in {"text", "list", "callout"}:
            prev = prev_by_section.get(section_key, "")
            if prev:
                n = max(20, int(_token_count(content) * overlap_ratio))
                n = min(n, 80)
                prefix = _tail_tokens(prev, n)
                if prefix:
                    content = f"{prefix}\n\n{content}"
            prev_by_section[section_key] = content
        ch2 = dict(ch)
        ch2["text"] = content
        out.append(ch2)
    return out


def parse_pdf(path: Path) -> list[dict]:
    cfg = DOC_CONFIG.get(path.name.lower(), {})
    source_document = cfg.get("source_document", path.stem)
    document_group = cfg.get("document_group", "irs_publication")
    topic = cfg.get("topic", "workplace_401k")

    rows: list[dict] = []
    hierarchy_stack: dict[str, str] = {"section": "§401"} if document_group == "us_code" else {}
    current_section = "Introduction" if document_group == "irs_publication" else "§401"

    with pdfplumber.open(path) as pdf:
        for p_idx, page in enumerate(pdf.pages, start=1):
            page_text = _extract_page_text(page)
            table_pairs = _extract_page_tables(page, page_number=p_idx)
            table_map = {k: v for k, v in table_pairs}
            for placeholder, _md in table_pairs:
                page_text = f"{page_text}\n{placeholder}"

            blocks = (
                _usc_blocks_from_text(page_text, p_idx)
                if document_group == "us_code"
                else _irs_blocks_from_text(page_text, p_idx)
            )

            for block_idx, block in enumerate(blocks):
                text, inferred_type = _restore_table_placeholders(block.text, table_map)
                chunk_type = inferred_type if inferred_type == "table" else block.block_type
                text = text.strip()
                if not text:
                    continue

                if document_group == "irs_publication":
                    first_line = text.splitlines()[0]
                    if _is_heading_irs(first_line) and chunk_type != "table":
                        current_section = first_line
                else:
                    first_line = text.splitlines()[0]
                    path_val, hierarchy_stack = _usc_path_for_line(first_line, hierarchy_stack)
                    current_section = path_val

                chunk_id = hashlib.sha1(
                    f"{source_document}|{p_idx}|{block_idx}|{current_section}|{text[:120]}".encode("utf-8")
                ).hexdigest()[:16]
                rows.append(
                    {
                        "id": f"{_slug(source_document)}_{chunk_id}",
                        "text": text,
                        "source": source_document,
                        "topic": topic,
                        "heading": current_section,
                        "source_document": source_document,
                        "page_number": p_idx,
                        "parent_section": current_section,
                        "document_group": document_group,
                        "chunk_type": chunk_type,
                    }
                )

    return _append_overlap(rows, overlap_ratio=0.12)


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_chunks(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    required = ("source_document", "page_number", "parent_section", "text")
    for idx, row in enumerate(rows):
        for key in required:
            if key not in row or row[key] in (None, "", []):
                errors.append(f"row={idx} missing required field: {key}")
        if row.get("chunk_type") == "table" and "|" not in row.get("text", ""):
            errors.append(f"row={idx} table chunk does not look markdown-formatted")
    return errors


def ingest_to_chroma(rows: list[dict], persist_dir: Path, collection_name: str) -> None:
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name=collection_name)

    ids = [r["id"] for r in rows]
    docs = [r["text"] for r in rows]
    metadatas = []
    for r in rows:
        meta = {k: v for k, v in r.items() if k not in {"id", "text"}}
        if isinstance(meta.get("page_number"), int):
            meta["page_number"] = int(meta["page_number"])
        metadatas.append(meta)

    batch = 128
    for i in range(0, len(rows), batch):
        collection.upsert(
            ids=ids[i : i + batch],
            documents=docs[i : i + batch],
            metadatas=metadatas[i : i + batch],
        )


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    default_pdf_dir = root / "data" / "rag_pdfs"
    default_jsonl = root / "data" / "rag_index" / "legal_chunks.jsonl"
    default_vec = root / "data" / "rag_vector"

    ap = argparse.ArgumentParser(description="Ingest structured legal/tax PDFs into Chroma vector store.")
    ap.add_argument("--pdf-dir", type=Path, default=default_pdf_dir)
    ap.add_argument("--out-jsonl", type=Path, default=default_jsonl)
    ap.add_argument("--vector-dir", type=Path, default=default_vec)
    ap.add_argument("--collection", type=str, default="finlit_hard_rules")
    ap.add_argument("--files", nargs="*", default=DEFAULT_PDFS)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)

    all_rows: list[dict] = []
    for fn in args.files:
        pdf_path = args.pdf_dir / fn
        if not pdf_path.exists():
            log.warning("Skipping missing PDF: %s", pdf_path)
            continue
        log.info("Parsing %s", pdf_path.name)
        rows = parse_pdf(pdf_path)
        log.info("Generated %d chunks from %s", len(rows), pdf_path.name)
        all_rows.extend(rows)

    if not all_rows:
        log.error("No chunks generated. Check --pdf-dir and --files.")
        return 1

    validation_errors = validate_chunks(all_rows)
    if validation_errors:
        for err in validation_errors[:20]:
            log.error("Validation: %s", err)
        if len(validation_errors) > 20:
            log.error("Validation: ... and %d more errors", len(validation_errors) - 20)
        return 2

    write_jsonl(all_rows, args.out_jsonl)
    ingest_to_chroma(all_rows, args.vector_dir, args.collection)
    log.info("Wrote %d chunks to %s", len(all_rows), args.out_jsonl)
    log.info("Persisted vector collection '%s' to %s", args.collection, args.vector_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
