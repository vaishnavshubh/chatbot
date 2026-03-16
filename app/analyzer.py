"""
Sends the user's message + the phase-specific analyzer skill prompt
to the LLM and parses structured JSON facts from the response.
"""

import json
import logging
from openai import OpenAI

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
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": skill_prompt},
                    {
                        "role": "system",
                        "content": (
                            "Current conversation state:\n"
                            f"{state_summary}\n\n"
                            "Return ONLY a flat JSON object with extracted fields. "
                            "Use dotted keys for nested fields (e.g. \"budget.fixed_expenses\"). "
                            "Omit fields you cannot confidently extract."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            raw = json.loads(resp.choices[0].message.content)
            if not isinstance(raw, dict):
                return {}
            return _flatten(raw)

        except Exception as exc:
            log.warning("Analyzer error: %s", exc)
            return {}
