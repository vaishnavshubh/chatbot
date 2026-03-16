"""
Deterministic PDF artifact generator.
Converts the plan text + state into a downloadable PDF.
"""

import re
from fpdf import FPDF

from state import ChatbotState

GOAL_DISPLAY = {
    "financial_foundations": "Financial Foundations",
    "budget_cashflow": "Budget & Cash Flow",
    "credit_management": "Credit Management",
    "workplace_401k": "Workplace 401(k)",
    "student_loans": "Student Loans",
    "borrowing_basics": "Borrowing Basics",
}

HORIZON_DISPLAY = {
    "short_term": "Short-term (< 6 months)",
    "medium_term": "Medium-term (6-24 months)",
    "long_term": "Long-term (2+ years)",
}


def _clean(text: str) -> str:
    """Strip markdown syntax and replace non-latin-1 characters."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = (
        text.replace("\u2014", "--")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
        .replace("\u2022", "-")
        .replace("\u00a0", " ")
    )
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _write_line(pdf: FPDF, text: str, h: float = 6):
    """Write a single multi_cell line, resetting X to left margin first."""
    pdf.set_x(pdf.l_margin)
    try:
        pdf.multi_cell(w=0, h=h, text=text)
    except Exception:
        pass


def generate_pdf(state: ChatbotState, plan_text: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Title ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(w=0, h=14, text="Financial Literacy Plan", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)

    goal_name = GOAL_DISPLAY.get(
        state.goal.primary_goal or "", state.goal.primary_goal or "General"
    )
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(w=0, h=8, text=_clean(f"Topic: {goal_name}"), new_x="LMARGIN", new_y="NEXT", align="C")

    horizon = HORIZON_DISPLAY.get(state.goal.time_horizon or "", "")
    if horizon:
        pdf.cell(w=0, h=8, text=_clean(f"Horizon: {horizon}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # ── Disclaimer ──────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 9)
    _write_line(
        pdf,
        _clean(
            "This document contains educational information only -- not "
            "personalized financial advice. Consult a qualified financial "
            "advisor for decisions specific to your situation."
        ),
        h=5,
    )
    pdf.ln(6)

    # ── Plan body ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 11)

    for raw_line in plan_text.split("\n"):
        line = _clean(raw_line.strip())

        if line.startswith("### "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            _write_line(pdf, line[4:], h=7)
            pdf.set_font("Helvetica", "", 11)

        elif line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 14)
            _write_line(pdf, line[3:], h=8)
            pdf.set_font("Helvetica", "", 11)

        elif line.startswith("# "):
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 16)
            _write_line(pdf, line[2:], h=9)
            pdf.set_font("Helvetica", "", 11)

        elif line.startswith(("- [ ] ", "- [x] ", "- ")):
            bullet_text = re.sub(r"^- \[.\] ", "", line)
            bullet_text = re.sub(r"^- ", "", bullet_text)
            _write_line(pdf, f"   -  {bullet_text}")

        elif re.match(r"^\d+\.\s", line):
            _write_line(pdf, f"   {line}")

        elif line == "---":
            pdf.ln(3)

        elif line:
            _write_line(pdf, line)

        else:
            pdf.ln(3)

    # ── Footer disclaimer ───────────────────────────────────────────
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    _write_line(
        pdf,
        _clean(
            "This is educational information, not personalized financial advice. "
            "Consider consulting a qualified financial advisor for decisions "
            "specific to your situation."
        ),
        h=5,
    )

    return pdf.output()
