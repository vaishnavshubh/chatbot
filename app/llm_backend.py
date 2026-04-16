"""
Unified chat completion for OpenAI-compatible APIs vs Google Gemini (google-genai).

Provider priority:
  1. NVIDIA_API_KEY → NVIDIA NIM (OpenAI-compatible, default: meta/llama-3.3-70b-instruct)
  2. GEMINI_API_KEY / GOOGLE_API_KEY → Gemini API (default: gemini-2.5-flash)
  3. OPENAI_API_KEY (+ optional OPENAI_BASE_URL) → OpenAI / Ollama / any compatible API

Multimodal: user turns may use structured "content" (text + optional images).
See message_content helpers below.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Protocol

log = logging.getLogger(__name__)

# Provider defaults
DEFAULT_NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_GEMMA4_TAG = "gemma4:latest"


def _forced_provider() -> str | None:
    """
    Optional override for provider routing.
    Supported values: auto, nvidia, gemini, openai
    """
    raw = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if raw in ("", "auto"):
        return None
    if raw in ("nvidia", "gemini", "openai"):
        return raw
    log.warning("Unknown LLM_PROVIDER=%r; falling back to automatic provider selection.", raw)
    return None


def use_nvidia() -> bool:
    forced = _forced_provider()
    if forced and forced != "nvidia":
        return False
    return bool(os.getenv("NVIDIA_API_KEY"))


def use_gemini() -> bool:
    forced = _forced_provider()
    if forced and forced != "gemini":
        return False
    return not use_nvidia() and bool(
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )


def resolve_model() -> str:
    explicit = os.getenv("LLM_MODEL")
    if explicit:
        # NVIDIA NIM model ids are repository-like (e.g. "meta/llama-3.3-70b-instruct").
        # If an Ollama-style tag is supplied while NVIDIA is selected, fall back safely.
        if use_nvidia() and ":" in explicit and "/" not in explicit:
            log.warning(
                "LLM_MODEL=%r looks like an Ollama tag but NVIDIA provider is active; "
                "falling back to %r.",
                explicit,
                DEFAULT_NVIDIA_MODEL,
            )
            return DEFAULT_NVIDIA_MODEL
        return explicit
    if use_nvidia():
        return DEFAULT_NVIDIA_MODEL
    if use_gemini():
        return DEFAULT_GEMINI_MODEL
    return DEFAULT_OLLAMA_GEMMA4_TAG


def text_user_message(text: str) -> dict[str, Any]:
    """Plain-text user message (backward compatible)."""
    return {"role": "user", "content": text}


def multimodal_user_message(text: str, images: list[tuple[bytes, str]]) -> dict[str, Any]:
    """
    User message with images. Each image is (raw_bytes, mime_type), e.g. ("image/png").
    """
    parts: list[dict[str, Any]] = [{"type": "text", "text": text or "(see attached image)"}]
    for data, mime_type in images:
        parts.append({"type": "image", "mime_type": mime_type, "data": data})
    return {"role": "user", "content": parts}


def message_from_history_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Map a stored chat dict (role, content, optional images) to an LLM message."""
    role = entry.get("role", "user")
    content = entry.get("content", "")
    images = entry.get("images") or []
    if role == "user" and images:
        raw_images: list[tuple[bytes, str]] = []
        for im in images:
            if isinstance(im, dict) and "data" in im and "mime_type" in im:
                raw_images.append((im["data"], im["mime_type"]))
        if raw_images:
            return multimodal_user_message(str(content), raw_images)
    return {"role": role, "content": content}


class ChatBackend(Protocol):
    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> str: ...


class OpenAIChatBackend:
    def __init__(self, client: Any):
        self._client = client

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        model = resolve_model()
        oa_messages = [_to_openai_message(m) for m in messages]
        resp = self._client.chat.completions.create(
            model=model,
            messages=oa_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        return (content or "").strip()


def _to_openai_message(m: dict[str, Any]) -> dict[str, Any]:
    role = m.get("role", "user")
    content = m.get("content", "")
    if isinstance(content, str):
        return {"role": role, "content": content}
    parts_out: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts_out.append({"type": "text", "text": block.get("text", "")})
        elif block.get("type") == "image":
            mime = block.get("mime_type") or "image/png"
            data = block.get("data")
            if not isinstance(data, (bytes, bytearray)):
                continue
            b64 = base64.standard_b64encode(bytes(data)).decode("ascii")
            parts_out.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )
    if not parts_out:
        return {"role": role, "content": ""}
    return {"role": role, "content": parts_out}


class GeminiChatBackend:
    def __init__(self, client: Any):
        self._client = client

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
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
                if isinstance(content, str):
                    system_chunks.append(content)
                continue
            gemini_role = "model" if role == "assistant" else "user"
            parts = _gemini_parts_from_content(content)
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=parts,
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


def _gemini_parts_from_content(content: Any) -> list[Any]:
    from google.genai import types

    if isinstance(content, str):
        return [types.Part(text=content)]

    parts: list[Any] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(types.Part(text=block.get("text", "") or " "))
        elif block.get("type") == "image":
            data = block.get("data")
            mime = block.get("mime_type") or "image/png"
            if isinstance(data, (bytes, bytearray)):
                parts.append(types.Part.from_bytes(data=bytes(data), mime_type=mime))
    if not parts:
        return [types.Part(text=" ")]
    return parts
