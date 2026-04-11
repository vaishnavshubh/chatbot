"""
Sends the user's message + the phase-specific analyzer skill prompt
to the LLM and parses structured JSON facts from the response.
"""

import json
import logging
import re

from llm_backend import ChatBackend, multimodal_user_message
from state import ChatbotState

log = logging.getLogger(__name__)


def _flatten(data: dict, prefix: str = "") -> dict:
    """Flatten nested dicts so {'budget': {'fixed_expenses': 1800}}
    becomes {'budget.fixed_expenses': 1800}."""
    flat: dict = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, full_key))
        else:
            flat[full_key] = value
    return flat


def _extract_json(text: str) -> dict:
    """Pull the first JSON object from LLM output, even if surrounded by text."""
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


class Analyzer:
    def __init__(self, backend: ChatBackend):
        self._backend = backend

    def run(
        self,
        user_message: str,
        skill_prompt: str,
        state: ChatbotState,
        images: list[tuple[bytes, str]] | None = None,
    ) -> dict:
        state_summary = json.dumps(state.model_dump(), default=str, indent=2)

        messages: list[dict] = [
            {"role": "system", "content": skill_prompt},
            {
                "role": "system",
                "content": (
                    "Current conversation state:\n"
                    f"{state_summary}\n\n"
                    "IMPORTANT: You MUST respond with ONLY a valid JSON object. "
                    "No markdown, no explanation, no extra text. "
                    "Use dotted keys for nested fields (e.g. \"budget.fixed_expenses\"). "
                    "Omit fields you cannot confidently extract. "
                    "If the user attached images (receipts, statements, screenshots), "
                    "read numbers and text from them when confident. "
                    "Example: {\"consent_acknowledged\": true, \"output_preference\": \"chat\"}"
                ),
            },
        ]
        if images:
            messages.append(
                multimodal_user_message(
                    user_message
                    or "Extract structured fields from the attached image(s) per your instructions.",
                    images,
                )
            )
        else:
            messages.append({"role": "user", "content": user_message})

        try:
            raw_text = self._backend.complete(
                messages=messages,
                max_tokens=500,
                temperature=0.1,
            )
            log.info("Analyzer raw response: %s", raw_text)
            raw = _extract_json(raw_text)
            return _flatten(raw)

        except Exception as exc:
            log.warning("Analyzer error: %s", exc)
            return {}
