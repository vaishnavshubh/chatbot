"""
Unified chat completion for OpenAI-compatible APIs vs Google Gemini (google-genai).

Set GEMINI_API_KEY (or GOOGLE_API_KEY) to use Gemini + Gemma models.
Otherwise use OpenAI SDK with OPENAI_API_KEY and optional OPENAI_BASE_URL.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

log = logging.getLogger(__name__)

# Project defaults: Gemma 4 everywhere (hosted via Gemini API, or local via Ollama tag).
DEFAULT_GEMINI_GEMMA4_MODEL = "gemma-4-26b-a4b-it"
DEFAULT_OLLAMA_GEMMA4_TAG = "gemma4:latest"


def use_gemini() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def resolve_model() -> str:
    if use_gemini():
        return os.getenv("LLM_MODEL", DEFAULT_GEMINI_GEMMA4_MODEL)
    return os.getenv("LLM_MODEL", DEFAULT_OLLAMA_GEMMA4_TAG)


class ChatBackend(Protocol):
    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str: ...


class OpenAIChatBackend:
    def __init__(self, client: Any):
        self._client = client

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        model = resolve_model()
        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        return (content or "").strip()


class GeminiChatBackend:
    def __init__(self, client: Any):
        self._client = client

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        from google.genai import types

        model = resolve_model()
        system_chunks: list[str] = []
        contents: list[Any] = []

        for m in messages:
            role, content = m.get("role", ""), m.get("content", "")
            if role == "system":
                system_chunks.append(content)
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)],
                )
            )

        system_instruction = "\n\n".join(system_chunks) if system_chunks else None
        cfg_kw: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            cfg_kw["system_instruction"] = system_instruction
        config = types.GenerateContentConfig(**cfg_kw)

        if not contents:
            # Opening turn can be system-only (e.g. Phase 0 welcome); Gemini needs a user turn.
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part(text="(Begin the conversation as instructed.)")],
                )
            ]

        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        text = getattr(response, "text", None)
        if text:
            return text.strip()

        # Fallback if .text is empty (e.g. safety / structure)
        try:
            cand = response.candidates[0]
            parts = cand.content.parts
            out: list[str] = []
            for p in parts:
                if getattr(p, "text", None):
                    out.append(p.text)
            return "\n".join(out).strip()
        except (IndexError, AttributeError, TypeError) as exc:
            log.warning("Gemini empty or unparsable response: %s", exc)
            return ""
