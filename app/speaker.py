"""
Sends the orchestrator's instruction payload + the phase-specific
speaker skill prompt to the LLM and returns a conversational response.
"""

import json
import logging
import os
from openai import OpenAI

log = logging.getLogger(__name__)

MODEL = os.getenv("LLM_MODEL", "llama4:latest")


class Speaker:
    def __init__(self, client: OpenAI):
        self.client = client

    def run(
        self,
        skill_prompt: str,
        instruction: dict,
        history: list[dict] | None = None,
        max_tokens: int = 2000,
    ) -> str:
        messages: list[dict] = [
            {"role": "system", "content": skill_prompt},
            {
                "role": "system",
                "content": (
                    "Orchestrator instruction (follow these directions):\n"
                    + json.dumps(instruction, default=str, indent=2)
                ),
            },
        ]

        if history:
            for msg in history[-10:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        try:
            resp = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content

        except Exception as exc:
            log.warning("Speaker error: %s", exc)
            return (
                "I'm having trouble processing that right now. "
                "Could you try again?"
            )
