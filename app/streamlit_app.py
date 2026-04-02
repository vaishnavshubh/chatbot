"""
Streamlit chat UI for the Financial Literacy Chatbot.

Run from the project root:
    streamlit run app/streamlit_app.py
"""

import os
import sys
import uuid
import logging
import re
from pathlib import Path

# Ensure sibling modules are importable when Streamlit runs this file directly.
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from state import ChatbotState
from phase_registry import PhaseRegistry
from analyzer import Analyzer
from speaker import Speaker
from orchestrator import Orchestrator, SkillLoader

# ── Paths ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MD_DIR = PROJECT_ROOT / "md"
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)
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

_MD_PLAN_HINTS = (
    r"(^|\n)##\s+|(^|\n)###\s+|(^|\n)- \[ \]\s+|(^|\n)\*\*Your Situation\*\*"
)


def _looks_like_plan_markdown(text: str) -> bool:
    """Heuristic: keep markdown rendering for Phase 4 plan-like responses."""
    return bool(re.search(_MD_PLAN_HINTS, text))


def _escape_markdown(text: str) -> str:
    """Escape markdown special chars for clean plain-text rendering."""
    # Escape backslashes first
    text = text.replace("\\", "\\\\")
    for ch in ["*", "_", "`"]:
        text = text.replace(ch, f"\\{ch}")
    return text


def _render_message(role: str, content: str) -> None:
    """
    Render a message. For assistant non-plan messages, avoid markdown emphasis artifacts
    by escaping markdown characters.
    """
    if role == "assistant" and not _looks_like_plan_markdown(content):
        st.markdown(_escape_markdown(content))
    else:
        st.markdown(content)


# ── Page config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Literacy Guide",
    page_icon="\U0001f4b0",
    layout="centered",
)


# ── Cached resources (created once per server lifetime) ─────────────────
@st.cache_resource
def _build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error(
            "**OPENAI_API_KEY not found.**  \n"
            "Create a `.env` file in the project root with:  \n"
            "`OPENAI_API_KEY=sk-...`"
        )
        st.stop()
    base_url = os.getenv("OPENAI_BASE_URL", None)
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)


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
    client = _build_openai_client()
    return Orchestrator(
        registry=_build_registry(),
        analyzer=Analyzer(client),
        speaker=Speaker(client),
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


def _reset_session():
    st.session_state.state = ChatbotState(session_id=str(uuid.uuid4()))
    st.session_state.messages = []
    st.session_state.initialized = False


# ── Sidebar ─────────────────────────────────────────────────────────────
def _render_sidebar():
    state: ChatbotState = st.session_state.state

    st.sidebar.title("Progress")
    for pid, label in PHASE_LABELS.items():
        if pid < state.current_phase:
            st.sidebar.markdown(f"\u2705  **{label}**")
        elif pid == state.current_phase:
            st.sidebar.markdown(f"\u25b6\ufe0f  **{label}**")
        else:
            st.sidebar.markdown(f"\u2b1c  {label}")

    st.sidebar.divider()
    st.sidebar.markdown("### Collected Info")

    if state.profile.life_stage:
        st.sidebar.markdown(
            f"**Stage:** {state.profile.life_stage.replace('_', ' ').title()}"
        )
    if state.profile.pay_type:
        st.sidebar.markdown(f"**Pay:** {state.profile.pay_type.title()}")
    if state.profile.income_range:
        st.sidebar.markdown(
            f"**Income:** {state.profile.income_range.replace('_', ' ')}"
        )
    if state.goal.primary_goal:
        st.sidebar.markdown(
            f"**Goal:** {GOAL_DISPLAY.get(state.goal.primary_goal, state.goal.primary_goal)}"
        )
    if state.output_preference:
        st.sidebar.markdown(f"**Output:** {state.output_preference.upper()}")

    if os.getenv("RAG_ENABLED", "1").lower() not in ("1", "true", "yes"):
        st.sidebar.caption("RAG: disabled (`RAG_ENABLED` is off)")
    else:
        rr = _build_rag_retriever()
        if rr is not None and getattr(rr, "enabled", False):
            st.sidebar.caption("RAG: on (Phase 4 plan uses curated excerpts)")
        else:
            st.sidebar.caption(
                "RAG: index missing — run `python app/rag/ingest.py` from project root"
            )

    # Session complete?
    if state.selected_next_action:
        st.sidebar.divider()
        st.sidebar.success(
            f"**Your commitment:**  \n{state.selected_next_action}"
        )

    st.sidebar.divider()
    if st.sidebar.button("\U0001f504 Start Over"):
        _reset_session()
        st.rerun()


# ── Main ────────────────────────────────────────────────────────────────
def main():
    _init_session()
    orchestrator = _build_orchestrator()

    st.title("\U0001f4b0 Financial Literacy Guide")
    _render_sidebar()

    # Generate the opening message on first load
    if not st.session_state.initialized:
        with st.spinner("Starting up..."):
            opening = orchestrator.generate_opening(st.session_state.state)
        st.session_state.messages.append({"role": "assistant", "content": opening})
        st.session_state.initialized = True

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            _render_message(msg["role"], msg["content"])

    # Handle new user input
    if user_input := st.chat_input("Type your message..."):
        # Display user message immediately
        with st.chat_message("user"):
            _render_message("user", user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Process through the orchestrator
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response, new_state, artifacts = orchestrator.handle_message(
                    user_input,
                    st.session_state.state,
                    st.session_state.messages,
                )
            _render_message("assistant", response)

        # Update session state
        st.session_state.state = new_state
        st.session_state.messages.append({"role": "assistant", "content": response})

        st.rerun()


if __name__ == "__main__":
    main()
