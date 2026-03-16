"""
Sends the user's message + the phase-specific analyzer skill prompt
to the LLM and parses structured JSON facts from the response.
"""

import json
import logging
import os
import re
from openai import OpenAI

from state import ChatbotState

log = logging.getLogger(__name__)

MODEL = os.getenv("LLM_MODEL", "llama4:latest")


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
    # Try parsing the whole response first
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Look for JSON inside ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Look for any { ... } block
    brace_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


class Analyzer:
    def __init__(self, client: OpenAI):
        self.client = client

    def run(
        self,
        user_message: str,
        skill_prompt: str,
        state: ChatbotState,
    ) -> dict:
        state_summary = json.dumps(state.model_dump(), default=str, indent=2)

        try:
            resp = self.client.chat.completions.create(
                model=MODEL,
                messages=[
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
                            "Example: {\"consent_acknowledged\": true, \"output_preference\": \"chat\"}"
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            raw_text = resp.choices[0].message.content
            log.info("Analyzer raw response: %s", raw_text)
            raw = _extract_json(raw_text)
            return _flatten(raw)

        except Exception as exc:
            log.warning("Analyzer error: %s", exc)
            return {}
