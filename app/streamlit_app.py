"""
Streamlit chat UI for the Financial Literacy Chatbot.

Run from the project root:
    streamlit run app/streamlit_app.py
"""

import base64
import html
import io
import os
import sys
import uuid
import logging
import re
from pathlib import Path

# Ensure sibling modules are importable when Streamlit runs this file directly.
sys.path.insert(0, str(Path(__file__).parent))

# ── Paths (before dotenv / Streamlit) ───────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MD_DIR = PROJECT_ROOT / "md"
ENV_PATH = PROJECT_ROOT / ".env"
ASSETS_DIR = PROJECT_ROOT / "assets"
LOGO_PNG = ASSETS_DIR / "finlit_logo.png"
LOGO_SVG = ASSETS_DIR / "finlit_logo.svg"

# FinLit brand greens (aligned with logo)
THEME = {
    "primary": "#1B5E20",
    "primary_mid": "#2E7D32",
    "accent": "#43A047",
    "light": "#E8F5E9",
}

from dotenv import load_dotenv

load_dotenv(ENV_PATH)

import streamlit as st

from secrets_util import apply_streamlit_secrets_to_environ

apply_streamlit_secrets_to_environ(st)

# Trim accidental spaces from .env / secrets values (e.g. KEY= mykey).
for _env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
    _v = os.getenv(_env_name)
    if _v is not None:
        os.environ[_env_name] = _v.strip()

from openai import OpenAI

from llm_backend import GeminiChatBackend, OpenAIChatBackend, use_gemini
from state import ChatbotState
from phase_registry import PhaseRegistry
from analyzer import Analyzer
from speaker import Speaker
from orchestrator import Orchestrator, SkillLoader

logging.basicConfig(level=logging.INFO)

# ── Constants ───────────────────────────────────────────────────────────
PHASE_LABELS = {
    0: "Consent & Setup",
    1: "Baseline Profile",
    2: "Goal Selection",
    3: "Evidence Intake",
    4: "Plan Generation",
    5: "Follow-up",
}

GOAL_DISPLAY = {
    "financial_foundations": "Financial Foundations",
    "budget_cashflow": "Budget & Cash Flow",
    "credit_management": "Credit Management",
    "workplace_401k": "Workplace 401(k)",
    "student_loans": "Student Loans",
    "borrowing_basics": "Borrowing Basics",
}

PAY_FREQ_DISPLAY = {
    "weekly": "Weekly",
    "biweekly": "Biweekly",
    "semi_monthly": "Twice monthly",
    "monthly": "Monthly",
}

HORIZON_DISPLAY = {
    "short_term": "Short term (< 6 months)",
    "medium_term": "Medium term (6–24 months)",
    "long_term": "Long term (2+ years)",
}

_MD_PLAN_HINTS = (
    r"(^|\n)##\s+|(^|\n)###\s+|(^|\n)- \[ \]\s+|(^|\n)\*\*Your Situation\*\*"
)


def _looks_like_plan_markdown(text: str) -> bool:
    """Heuristic: keep markdown rendering for Phase 4 plan-like responses."""
    return bool(re.search(_MD_PLAN_HINTS, text))


def _render_plan_markdown(content: str) -> None:
    """Plan keeps ## / lists; normalize entities and avoid $...$ math mode."""
    text = html.unescape(content)
    text = text.replace("$", r"\$")
    st.markdown(text)


def _render_plain_chat(text: str) -> None:
    """
    Show assistant/user chat as readable plain text.

    - Models sometimes emit HTML entities (e.g. &#x27;). html.escape() would turn
      the '&' into &amp; and break them unless we unescape first.
    - Streamlit markdown parses $...$ as math (red/error styling). Replacing $
      with &#36; keeps dollar amounts readable without LaTeX.
    """
    text = html.unescape(text)
    safe = html.escape(text, quote=False)
    safe = safe.replace("$", "&#36;")
    st.markdown(
        '<div style="white-space: pre-wrap; font-family: sans-serif;">'
        f"{safe}</div>",
        unsafe_allow_html=True,
    )


def _render_message(role: str, content: str) -> None:
    """
    Plan responses use markdown. Everything else is plain text so dollar amounts
    and asterisks from the model do not turn into math or garbled emphasis.
    """
    if role == "assistant" and _looks_like_plan_markdown(content):
        _render_plan_markdown(content)
    else:
        _render_plain_chat(content)


def _titlize_enum(value: str) -> str:
    return value.replace("_", " ").title()


def _format_money(value: float | None) -> str | None:
    if value is None:
        return None
    if value == int(value):
        return f"${int(value):,}"
    return f"${value:,.2f}"


def _logo_html(max_width_px: int = 240) -> str | None:
    """Return <img> data-URI for bundled logo (PNG preferred, else SVG)."""
    path = LOGO_PNG if LOGO_PNG.exists() else LOGO_SVG if LOGO_SVG.exists() else None
    if path is None:
        return None
    raw = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/svg+xml"
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return (
        f'<img src="data:{mime};base64,{b64}" '
        f'style="max-width:{max_width_px}px;width:100%;height:auto;display:block;" '
        'alt="FinLit logo" />'
    )


def _inject_theme_css() -> None:
    p, pm, ac, lg = (
        THEME["primary"],
        THEME["primary_mid"],
        THEME["accent"],
        THEME["light"],
    )
    st.markdown(
        f"""
        <style>
        .finlit-main-title {{
            color: {p};
            font-weight: 700;
            font-size: 1.75rem;
            margin: 0;
            line-height: 1.2;
        }}
        .finlit-subtitle {{
            color: {pm};
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {lg} 0%, #ffffff 55%) !important;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: #1b1b1b;
        }}
        button[kind="primary"] {{
            background-color: {pm} !important;
            border-color: {pm} !important;
        }}
        [data-testid="stChatInput"] textarea {{
            border-color: {ac} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _collected_info_rows(state: ChatbotState) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if state.consent_acknowledged:
        rows.append(("Consent", "Acknowledged"))
    if state.output_preference:
        rows.append(("Output preference", state.output_preference.title()))

    p = state.profile
    if p.life_stage:
        rows.append(("Life stage", _titlize_enum(p.life_stage)))
    if p.pay_type:
        rows.append(("Pay type", _titlize_enum(p.pay_type)))
    if p.pay_frequency:
        rows.append(
            ("Pay frequency", PAY_FREQ_DISPLAY.get(p.pay_frequency, p.pay_frequency))
        )
    if p.income_range:
        rows.append(("Income range", p.income_range.replace("_", " ").upper()))

    g = state.goal
    if g.primary_goal:
        rows.append(
            ("Primary goal", GOAL_DISPLAY.get(g.primary_goal, g.primary_goal))
        )
    if g.time_horizon:
        rows.append(
            ("Time horizon", HORIZON_DISPLAY.get(g.time_horizon, g.time_horizon))
        )

    b = state.budget
    for label, val in (
        ("Monthly fixed expenses", _format_money(b.fixed_expenses)),
        ("Monthly variable expenses", _format_money(b.variable_expenses)),
    ):
        if val is not None:
            rows.append((label, val))

    c = state.credit
    if c.apr is not None:
        rows.append(("Credit APR", f"{c.apr:g}%"))
    if c.balance is not None:
        bal = _format_money(c.balance)
        if bal:
            rows.append(("Credit balance", bal))
    if c.minimum_payment is not None:
        mp = _format_money(c.minimum_payment)
        if mp:
            rows.append(("Minimum payment", mp))
    if c.due_date:
        rows.append(("Payment due", c.due_date))

    r = state.retirement
    if r.employer_match:
        rows.append(("Employer match", r.employer_match))
    if r.contribution_rate is not None:
        rows.append(("401(k) contribution", f"{r.contribution_rate:g}%"))

    ln = state.loan
    if ln.principal is not None:
        pr = _format_money(ln.principal)
        if pr:
            rows.append(("Loan principal", pr))
    if ln.interest_rate is not None:
        rows.append(("Loan interest rate", f"{ln.interest_rate:g}%"))
    if ln.payment_amount is not None:
        pay = _format_money(ln.payment_amount)
        if pay:
            rows.append(("Loan payment", pay))

    if state.plan_generated:
        rows.append(("Educational plan", "Generated"))
    if state.evidence_skipped:
        rows.append(("Evidence intake", "Skipped (general plan)"))

    return rows


# ── Page config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinLit Guide",
    page_icon="\U0001f331",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── Cached resources (created once per server lifetime) ─────────────────
@st.cache_resource
def _build_llm_backend():
    """Gemini API (GEMINI_API_KEY) or OpenAI-compatible API (OPENAI_API_KEY)."""
    if use_gemini():
        from google import genai

        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        if not key:
            st.error(
                "**GEMINI_API_KEY not found.**  \n"
                "Locally: set it in `.env` (see `.env.example`).  \n"
                "On **Streamlit Community Cloud**: App settings → Secrets → add `GEMINI_API_KEY`.  \n"
                "Key: https://aistudio.google.com/apikey — or unset Gemini and use OpenAI / Ollama."
            )
            st.stop()
        client = genai.Client(api_key=key)
        return GeminiChatBackend(client)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error(
            "**OPENAI_API_KEY not found.**  \n"
            "Locally: add `OPENAI_API_KEY` to `.env` (see `.env.example`).  \n"
            "On **Streamlit Community Cloud**: App settings → Secrets → add `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL`).  \n"
            "Or set **GEMINI_API_KEY** to use Google Gemini / Gemma instead."
        )
        st.stop()
    base_url = os.getenv("OPENAI_BASE_URL", None)
    oa = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    return OpenAIChatBackend(oa)


@st.cache_resource
def _build_registry() -> PhaseRegistry:
    return PhaseRegistry(MD_DIR / "phase_registry.json")


@st.cache_resource
def _build_skill_loader() -> SkillLoader:
    return SkillLoader(MD_DIR)


@st.cache_resource
def _build_rag_retriever():
    """Keyword RAG over data/rag_index/chunks.jsonl (see Rag_implementation.md)."""
    if os.getenv("RAG_ENABLED", "1").lower() not in ("1", "true", "yes"):
        return None
    from rag.retrieval import RAGRetriever

    path = PROJECT_ROOT / "data" / "rag_index" / "chunks.jsonl"
    return RAGRetriever(path)


def _build_orchestrator() -> Orchestrator:
    backend = _build_llm_backend()
    return Orchestrator(
        registry=_build_registry(),
        analyzer=Analyzer(backend),
        speaker=Speaker(backend),
        skill_loader=_build_skill_loader(),
        rag_retriever=_build_rag_retriever(),
    )


# ── Session state helpers ───────────────────────────────────────────────
def _init_session():
    if "state" not in st.session_state:
        st.session_state.state = ChatbotState(session_id=str(uuid.uuid4()))
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    if "upload_nonce" not in st.session_state:
        st.session_state.upload_nonce = 0


def _mime_from_upload(name: str, reported: str | None) -> str:
    if reported and str(reported).startswith("image/"):
        return str(reported)
    lower = (name or "").lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith((".heic", ".heif")):
        return "image/heic"
    return "image/jpeg"


_CSV_FENCE_RE = re.compile(r"```(?:csv)?\s*\n?([\s\S]*?)```", re.IGNORECASE)


def _extract_csv_blocks(text: str) -> list[str]:
    blocks = [b.strip() for b in _CSV_FENCE_RE.findall(text or "")]
    return [b for b in blocks if b and "," in b]


def _reset_session():
    st.session_state.state = ChatbotState(session_id=str(uuid.uuid4()))
    st.session_state.messages = []
    st.session_state.initialized = False


# ── Sidebar ─────────────────────────────────────────────────────────────
def _render_sidebar():
    state: ChatbotState = st.session_state.state
    sb = st.sidebar

    img_html = _logo_html(220)
    if img_html:
        sb.markdown(
            f'<div style="text-align:center;margin-bottom:0.25rem;">{img_html}</div>',
            unsafe_allow_html=True,
        )
        # Avoid repeating the tagline when the PNG already includes it in the artwork.
        if not LOGO_PNG.exists():
            sb.markdown(
                f'<p style="color:{THEME["primary_mid"]};font-size:0.72rem;text-align:center;'
                'letter-spacing:0.06em;margin:0 0 0.75rem 0;">'
                "EMPOWERING FINANCIAL FUTURES</p>",
                unsafe_allow_html=True,
            )
    else:
        sb.markdown(
            f'<p style="text-align:center;color:{THEME["primary"]};'
            f'font-weight:700;font-size:1.35rem;margin:0;">FinLit</p>'
            f'<p style="color:{THEME["primary_mid"]};font-size:0.72rem;text-align:center;'
            'letter-spacing:0.06em;margin:0.35rem 0 0.75rem 0;">'
            "EMPOWERING FINANCIAL FUTURES</p>",
            unsafe_allow_html=True,
        )

    sb.markdown("### Phases")
    for pid, label in PHASE_LABELS.items():
        if state.selected_next_action and pid <= 5:
            mark = "\u2705"
            style = f"color:{THEME['primary_mid']};"
        elif pid < state.current_phase:
            mark = "\u2705"
            style = f"color:{THEME['primary_mid']};"
        elif pid == state.current_phase:
            mark = "\u25b6"
            style = f"color:{THEME['primary']};font-weight:600;"
        else:
            mark = "\u25cb"
            style = "color:#9E9E9E;"
        sb.markdown(f'<p style="margin:0.2rem 0;{style}">{mark} {label}</p>', unsafe_allow_html=True)

    sb.divider()
    sb.markdown("### Collected info")
    rows = _collected_info_rows(state)
    if not rows:
        sb.info("Nothing captured yet — your answers will appear here as you chat.")
    else:
        for title, val in rows:
            sb.markdown(f"**{title}:** {val}")

    if os.getenv("RAG_ENABLED", "1").lower() not in ("1", "true", "yes"):
        sb.caption("RAG: disabled (`RAG_ENABLED` is off)")
    else:
        rr = _build_rag_retriever()
        if rr is not None and getattr(rr, "enabled", False):
            sb.caption("RAG: on (Phase 4 plan uses curated excerpts)")
        else:
            sb.caption(
                "RAG: index missing — run `python app/rag/ingest.py` from project root"
            )

    if state.selected_next_action:
        sb.divider()
        sb.success(f"**Your commitment:**  \n{state.selected_next_action}")

    sb.divider()
    if sb.button("\U0001f504 Start over", use_container_width=True):
        _reset_session()
        st.rerun()


# ── Main ────────────────────────────────────────────────────────────────
def main():
    _init_session()
    _inject_theme_css()
    _render_sidebar()
    orchestrator = _build_orchestrator()

    logo_html = _logo_html(100)
    c1, c2 = st.columns([1, 4])
    with c1:
        if logo_html:
            st.markdown(
                f'<div style="padding-top:4px;">{logo_html}</div>',
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown(
            '<p class="finlit-main-title">Financial literacy guide</p>'
            '<p class="finlit-subtitle">Personalized education — not financial advice.</p>',
            unsafe_allow_html=True,
        )

    # Generate the opening message on first load
    if not st.session_state.initialized:
        with st.spinner("Starting up..."):
            opening = orchestrator.generate_opening(st.session_state.state)
        st.session_state.messages.append({"role": "assistant", "content": opening})
        st.session_state.initialized = True

    uploaded_images = st.file_uploader(
        "Attach photo(s) — receipts, statements, or screenshots (optional)",
        type=["png", "jpg", "jpeg", "webp", "gif", "heic", "heif"],
        accept_multiple_files=True,
        key=f"chat_images_{st.session_state.upload_nonce}",
    )
    st.caption(
        "Vision: use a multimodal model (hosted Gemma 4 on the Gemini API, GPT-4o, etc.). "
        "Text-only models will fail when images are attached."
    )

    # Render chat history
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                for im in msg.get("images") or []:
                    try:
                        st.image(
                            io.BytesIO(im["data"]),
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption("(Could not preview this image type.)")
            _render_message(msg["role"], msg["content"])
            if msg["role"] == "assistant":
                for j, csv_body in enumerate(_extract_csv_blocks(msg["content"])):
                    st.download_button(
                        label="Download CSV"
                        if j == 0
                        else f"Download CSV ({j + 1})",
                        data=csv_body.encode("utf-8"),
                        file_name=f"finlit_budget_{idx}_{j}.csv",
                        mime="text/csv",
                        key=f"csv_dl_{idx}_{j}",
                    )

    # Handle new user input
    user_input = st.chat_input("Type your message...")
    if user_input is not None:
        files = list(uploaded_images) if uploaded_images else []
        image_payloads = []
        for uf in files:
            image_payloads.append(
                {
                    "mime_type": _mime_from_upload(uf.name, uf.type),
                    "data": uf.getvalue(),
                }
            )
        text = (user_input or "").strip()
        if not text and not image_payloads:
            st.warning("Add a message or attach at least one image.")
        else:
            display_text = text if text else "(See attached image(s).)"
            user_entry: dict = {
                "role": "user",
                "content": display_text,
            }
            if image_payloads:
                user_entry["images"] = image_payloads

            with st.chat_message("user"):
                for im in image_payloads:
                    try:
                        st.image(io.BytesIO(im["data"]), use_container_width=True)
                    except Exception:
                        st.caption("(Image attached — preview unavailable.)")
                _render_message("user", display_text)

            st.session_state.messages.append(user_entry)

            # Process through the orchestrator (history includes the new user turn)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response, new_state, artifacts = orchestrator.handle_message(
                        display_text,
                        st.session_state.state,
                        st.session_state.messages,
                    )
                _render_message("assistant", response)
                for j, csv_body in enumerate(_extract_csv_blocks(response)):
                    st.download_button(
                        label="Download CSV"
                        if j == 0
                        else f"Download CSV ({j + 1})",
                        data=csv_body.encode("utf-8"),
                        file_name=f"finlit_budget_new_{j}.csv",
                        mime="text/csv",
                        key=f"csv_new_{st.session_state.upload_nonce}_{j}",
                    )

            st.session_state.state = new_state
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.upload_nonce += 1
            st.rerun()


if __name__ == "__main__":
    main()
