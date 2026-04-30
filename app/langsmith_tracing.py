"""
Optional LangSmith tracing for LLM calls.

Enable with:
  LANGSMITH_TRACING=true
  LANGSMITH_API_KEY=lsv2_...

Optional:
  LANGSMITH_PROJECT=my-project

Legacy equivalents LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY / LANGCHAIN_PROJECT
also work.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


def ensure_traceable_client_env() -> None:
    """
    Map LANGSMITH_* into LANGCHAIN_* when tracing is on.

    The ``@traceable`` decorator and LangChain-style clients often read
    LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY; syncing avoids traces being dropped
    when only LANGSMITH_* is set.
    """
    if not is_langsmith_tracing_active():
        return
    if os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower() not in (
        "true",
        "1",
        "yes",
    ):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    key = (
        os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY") or ""
    ).strip()
    if key and not (os.getenv("LANGCHAIN_API_KEY") or "").strip():
        os.environ["LANGCHAIN_API_KEY"] = key
    proj = (
        os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or ""
    ).strip()
    if proj and not (os.getenv("LANGCHAIN_PROJECT") or "").strip():
        os.environ["LANGCHAIN_PROJECT"] = proj


def is_langsmith_tracing_active() -> bool:
    tracing_flag = (
        os.getenv("LANGSMITH_TRACING", "").strip().lower() in ("true", "1", "yes")
        or os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower() in ("true", "1", "yes")
    )
    key = (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY") or "").strip()
    return tracing_flag and bool(key)


def wrap_openai_for_tracing(client: Any) -> Any:
    """Return LangSmith-instrumented OpenAI client when tracing is configured."""
    if not is_langsmith_tracing_active():
        return client
    ensure_traceable_client_env()
    try:
        from langsmith.wrappers import wrap_openai
    except ImportError:
        log.warning(
            "LangSmith tracing is enabled but `langsmith` is not installed. "
            "Run: pip install langsmith"
        )
        return client
    project = (
        os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or ""
    ).strip()
    log.info(
        "LangSmith tracing enabled (OpenAI-compatible path; project=%s).",
        project or "(default workspace project)",
    )
    return wrap_openai(client)
