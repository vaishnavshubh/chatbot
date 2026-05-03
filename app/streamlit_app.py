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
LOGO_FUTURISTIC = ASSETS_DIR / "finlit_logo_futuristic.png"
LOGO_PNG = ASSETS_DIR / "finlit_logo.png"
LOGO_SVG = ASSETS_DIR / "finlit_logo.svg"

# Futuristic dark UI (ChatGPT / Gemini / Claude–inspired palette)
THEME = {
    "bg_deep": "#030508",
    "bg": "#0a0e14",
    "surface": "#0f141d",
    "surface_elevated": "#151b2a",
    "border": "rgba(99, 179, 237, 0.14)",
    "text": "#e8eef9",
    "text_muted": "#8a9bb8",
    "accent": "#22d3ee",
    "accent_dim": "#06b6d4",
    "violet": "#a78bfa",
    # Aliases for phase / sidebar accents
    "primary": "#a78bfa",
    "primary_mid": "#22d3ee",
    "light": "#0c1018",
}

from dotenv import load_dotenv

load_dotenv(ENV_PATH)

import streamlit as st

from secrets_util import apply_streamlit_secrets_to_environ

apply_streamlit_secrets_to_environ(st)

# Trim accidental spaces from .env / secrets values (e.g. KEY= mykey).
for _env_name in (
    "NVIDIA_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "LLM_PROVIDER",
    "RAG_PROFILE",
    "RAG_TOP_K",
    "RAG_MAX_CHUNKS_IN_PROMPT",
    "RAG_MAX_CHARS_PER_CHUNK",
    "RAG_BACKEND",
    "RAG_VECTOR_COLLECTION",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING_V2",
):
    _v = os.getenv(_env_name)
    if _v is not None:
        os.environ[_env_name] = _v.strip()

from openai import OpenAI

from langsmith_tracing import wrap_openai_for_tracing

from llm_backend import (
    GeminiChatBackend,
    OpenAIChatBackend,
    NVIDIA_BASE_URL,
    use_gemini,
    use_nvidia,
)
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


def _render_plain_chat(text: str, *, role: str) -> None:
    """
    Show assistant/user chat as readable plain text in a futuristic bubble.

    - Models sometimes emit HTML entities (e.g. &#x27;). html.escape() would turn
      the '&' into &amp; and break them unless we unescape first.
    - Streamlit markdown parses $...$ as math (red/error styling). Replacing $
      with &#36; keeps dollar amounts readable without LaTeX.
    """
    text = html.unescape(text)
    safe = html.escape(text, quote=False)
    safe = safe.replace("$", "&#36;")
    bubble = "finlit-bubble finlit-bubble-user" if role == "user" else "finlit-bubble finlit-bubble-assistant"
    st.markdown(
        f'<div class="{bubble}"><div class="finlit-bubble-inner">{safe}</div></div>',
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
        _render_plain_chat(content, role=role)


def _render_message_placeholder(
    container,
    role: str,
    content: str,
) -> None:
    """Same rules as ``_render_message``, but draw into a Streamlit container (e.g. ``st.empty()``)."""
    if role == "assistant" and _looks_like_plan_markdown(content):
        text = html.unescape(content)
        text = text.replace("$", r"\$")
        container.markdown(text)
    else:
        text = html.unescape(content)
        safe = html.escape(text, quote=False)
        safe = safe.replace("$", "&#36;")
        bubble = "finlit-bubble finlit-bubble-user" if role == "user" else "finlit-bubble finlit-bubble-assistant"
        container.markdown(
            f'<div class="{bubble}"><div class="finlit-bubble-inner">{safe}</div></div>',
            unsafe_allow_html=True,
        )


def _titlize_enum(value: str) -> str:
    return value.replace("_", " ").title()


def _format_money(value: float | None) -> str | None:
    if value is None:
        return None
    if value == int(value):
        return f"${int(value):,}"
    return f"${value:,.2f}"


def _logo_html(max_width_px: int = 240) -> str | None:
    """Return <img> data-URI (futuristic logo preferred, then legacy PNG/SVG)."""
    path = None
    for candidate in (LOGO_FUTURISTIC, LOGO_PNG, LOGO_SVG):
        if candidate.exists():
            path = candidate
            break
    if path is None:
        return None
    raw = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/svg+xml"
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return (
        f'<img src="data:{mime};base64,{b64}" '
        f'style="max-width:{max_width_px}px;width:100%;height:auto;display:block;border-radius:14px;" '
        'alt="FinLit AI logo" />'
    )


def _inject_theme_css() -> None:
    t = THEME
    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <style>
        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: radial-gradient(120% 80% at 50% -20%, rgba(34,211,238,0.08) 0%, transparent 50%),
                linear-gradient(180deg, {t["bg_deep"]} 0%, {t["bg"]} 40%, {t["bg"]} 100%) !important;
            color: {t["text"]} !important;
            font-family: "Inter", system-ui, -apple-system, sans-serif !important;
        }}
        [data-testid="stHeader"] {{
            background: transparent !important;
            border-bottom: 1px solid {t["border"]};
        }}
        [data-testid="stToolbar"] {{
            background: transparent !important;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(175deg, {t["surface"]} 0%, {t["bg_deep"]} 100%) !important;
            border-right: 1px solid {t["border"]} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] .stMarkdown {{
            color: {t["text_muted"]} !important;
        }}
        [data-testid="stSidebar"] h3 {{
            color: {t["text"]} !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em;
        }}
        .main .block-container {{
            padding-top: 1.25rem !important;
            max-width: 52rem !important;
        }}
        .finlit-main-title {{
            font-weight: 700;
            font-size: 1.65rem;
            margin: 0;
            line-height: 1.2;
            background: linear-gradient(105deg, {t["text"]} 0%, {t["accent"]} 45%, {t["violet"]} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .finlit-subtitle {{
            color: {t["text_muted"]};
            font-size: 0.92rem;
            margin-top: 0.35rem;
            font-weight: 400;
        }}
        .finlit-bubble {{
            border-radius: 18px;
            padding: 0.85rem 1.1rem;
            margin: 0.35rem 0 0.75rem 0;
            border: 1px solid {t["border"]};
            box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        }}
        .finlit-bubble-assistant {{
            background: linear-gradient(145deg, {t["surface_elevated"]} 0%, {t["surface"]} 100%);
            margin-right: 2rem;
        }}
        .finlit-bubble-user {{
            background: linear-gradient(145deg, rgba(34,211,238,0.12) 0%, {t["surface_elevated"]} 100%);
            margin-left: 2rem;
            border-color: rgba(34,211,238,0.25);
        }}
        .finlit-bubble-inner {{
            white-space: pre-wrap;
            color: {t["text"]};
            font-size: 0.95rem;
            line-height: 1.55;
        }}
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 {{
            color: {t["accent"]} !important;
        }}
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {{
            color: {t["text"]} !important;
        }}
        [data-testid="stChatMessage"] {{
            background: transparent !important;
        }}
        /* Full-width bottom bar (Streamlit pins chat input here — defaults to white) */
        .stApp > footer,
        footer[data-testid="stFooter"],
        [data-testid="stBottom"] {{
            background: {t["bg"]} !important;
            background-image: none !important;
            border-top: 1px solid {t["border"]} !important;
        }}
        [data-testid="stBottomBlockContainer"] {{
            background: transparent !important;
            padding-top: 0.5rem !important;
        }}
        .stChatFloatingInputContainer,
        [data-testid="stChatFloatingInputContainer"] {{
            background: transparent !important;
        }}
        [data-testid="stChatInput"],
        [data-testid="stChatInput"] > form,
        [data-testid="stChatInput"] .stForm {{
            background: {t["surface"]} !important;
            border-radius: 16px !important;
            border: 1px solid {t["border"]} !important;
            box-shadow: 0 0 0 1px rgba(167,139,250,0.08), 0 12px 40px rgba(0,0,0,0.4) !important;
        }}
        [data-testid="stChatInput"] [data-baseweb="base-input"],
        [data-testid="stChatInput"] [data-baseweb="textarea"] {{
            background-color: {t["surface"]} !important;
            border: none !important;
        }}
        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] textarea:focus {{
            color: {t["text"]} !important;
            background: {t["surface"]} !important;
            border: none !important;
            box-shadow: none !important;
            caret-color: {t["accent"]} !important;
        }}
        [data-testid="stChatInput"] textarea::placeholder {{
            color: {t["text_muted"]} !important;
            opacity: 0.85 !important;
        }}
        [data-testid="stChatInput"] button {{
            background: linear-gradient(135deg, {t["accent_dim"]} 0%, {t["violet"]} 100%) !important;
            color: #0a0e14 !important;
            border: none !important;
        }}
        [data-testid="stChatInput"] button:hover {{
            filter: brightness(1.08) !important;
        }}
        [data-testid="stChatInput"] [data-baseweb="base-input"] > div {{
            background: {t["surface"]} !important;
        }}
        .stFileUploader [data-testid="stFileUploader"] {{
            color: {t["text_muted"]} !important;
        }}
        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span {{
            color: {t["text_muted"]} !important;
        }}
        [data-testid="stFileUploader"] p {{
            color: {t["text"]} !important;
        }}
        .stCaption, [data-testid="stCaption"] {{
            color: {t["text_muted"]} !important;
        }}
        .stMainBlockContainer.block-container {{
            background: transparent !important;
        }}
        [data-testid="stMain"],
        section.main {{
            background: transparent !important;
        }}
        button[kind="primary"] {{
            background: linear-gradient(90deg, {t["accent_dim"]} 0%, {t["violet"]} 100%) !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }}
        button[kind="secondary"] {{
            background: {t["surface_elevated"]} !important;
            color: {t["text"]} !important;
            border: 1px solid {t["border"]} !important;
            border-radius: 10px !important;
        }}
        [data-testid="stBaseButton-secondary"] {{
            color: {t["text"]} !important;
        }}
        .stDownloadButton button {{
            background: {t["surface_elevated"]} !important;
            color: {t["accent"]} !important;
            border: 1px solid rgba(34,211,238,0.35) !important;
            border-radius: 10px !important;
        }}
        [data-testid="stFileUploader"] section {{
            background: {t["surface"]} !important;
            border: 1px dashed {t["border"]} !important;
            border-radius: 14px !important;
        }}
        [data-testid="stAlert"] {{
            background: {t["surface_elevated"]} !important;
            border: 1px solid {t["border"]} !important;
            color: {t["text"]} !important;
        }}
        div[data-baseweb="notification"] {{
            color: {t["text"]} !important;
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
    page_title="FinLit AI",
    page_icon="\U0001f4c8",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Cached resources (created once per server lifetime) ─────────────────
@st.cache_resource
def _build_llm_backend():
    """NVIDIA NIM, Gemini API, or generic OpenAI-compatible backend."""

    # --- NVIDIA NIM (highest priority) ---
    if use_nvidia():
        key = os.getenv("NVIDIA_API_KEY", "")
        if not key:
            st.error(
                "**NVIDIA_API_KEY not found.**  \n"
                "Locally: set it in `.env` (see `.env.example`).  \n"
                "On **Streamlit Community Cloud**: App settings → Secrets → add `NVIDIA_API_KEY`.  \n"
                "Key: https://build.nvidia.com/ → API Catalog → Get API Key."
            )
            st.stop()
        oa = OpenAI(api_key=key, base_url=NVIDIA_BASE_URL)
        oa = wrap_openai_for_tracing(oa)
        return OpenAIChatBackend(oa)

    # --- Google Gemini ---
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

    # --- OpenAI / Ollama / any compatible endpoint ---
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error(
            "**No LLM API key found.**  \n"
            "Set one of: `NVIDIA_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY` in `.env` "
            "(see `.env.example`).  \n"
            "On **Streamlit Community Cloud**: App settings → Secrets."
        )
        st.stop()
    base_url = os.getenv("OPENAI_BASE_URL", None)
    oa = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    oa = wrap_openai_for_tracing(oa)
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
    backend = (os.getenv("RAG_BACKEND") or "jsonl").strip().lower()
    if backend == "vector":
        try:
            from rag.retrieval_vector import RAGVectorRetriever

            vector_dir = PROJECT_ROOT / "data" / "rag_vector"
            collection = (os.getenv("RAG_VECTOR_COLLECTION") or "finlit_hard_rules").strip()
            return RAGVectorRetriever(vector_dir, collection_name=collection)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "RAG_BACKEND=vector failed (%s); falling back to jsonl chunks.",
                exc,
            )

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
        if not (LOGO_FUTURISTIC.exists() or LOGO_PNG.exists()):
            sb.markdown(
                f'<p style="color:{THEME["accent"]};font-size:0.68rem;text-align:center;'
                'letter-spacing:0.12em;margin:0 0 0.75rem 0;text-transform:uppercase;">'
                "AI · Financial futures</p>",
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
            style = f"color:{THEME['accent']};font-weight:600;text-shadow:0 0 12px rgba(34,211,238,0.35);"
        else:
            mark = "\u25cb"
            style = f"color:{THEME['text_muted']};"
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
            pass
        else:
            backend = (os.getenv("RAG_BACKEND") or "jsonl").strip().lower()
            if backend == "vector":
                sb.caption(
                    "RAG: vector index missing — run `python app/rag/ingest_pdf_vector.py` from project root"
                )
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
            '<p class="finlit-main-title">FinLit AI</p>'
            '<p class="finlit-subtitle">Your financial literacy copilot — educational only, not advice.</p>',
            unsafe_allow_html=True,
        )

    # Generate the opening message on first load (streamed); placeholder is cleared
    # so the chat history below renders a single assistant bubble (no duplicate).
    if not st.session_state.initialized:
        out_open: dict = {}
        ph = st.empty()
        acc_open: list[str] = []
        for chunk in orchestrator.generate_opening_stream(
            st.session_state.state, out_open
        ):
            acc_open.append(chunk)
            _render_message_placeholder(ph, "assistant", "".join(acc_open))
        opening = out_open.get("response", "".join(acc_open))
        st.session_state.messages.append({"role": "assistant", "content": opening})
        st.session_state.initialized = True
        ph.empty()

    uploaded_images = st.file_uploader(
        "Attach photo(s) — receipts, statements, or screenshots (optional)",
        type=["png", "jpg", "jpeg", "webp", "gif", "heic", "heif"],
        accept_multiple_files=True,
        key=f"chat_images_{st.session_state.upload_nonce}",
    )
    st.caption(
        "Vision requires a multimodal model (Gemini, GPT-4o, etc.). "
        "Text-only models (NVIDIA NIM, Ollama) will ignore or fail on attached images."
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
                out_msg: dict = {}
                ph = st.empty()
                acc_resp: list[str] = []
                for chunk in orchestrator.handle_message_stream(
                    display_text,
                    st.session_state.state,
                    st.session_state.messages,
                    out_msg,
                ):
                    acc_resp.append(chunk)
                    _render_message_placeholder(
                        ph, "assistant", "".join(acc_resp)
                    )
                response = out_msg.get("response", "".join(acc_resp))
                # Final pass applies safety redactions (may differ slightly from raw stream).
                _render_message_placeholder(ph, "assistant", response)
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

            # ``handle_message_stream`` mutates ``st.session_state.state`` in place.
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.upload_nonce += 1
            st.rerun()


if __name__ == "__main__":
    main()
