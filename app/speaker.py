"""
Sends the orchestrator's instruction payload + the phase-specific
speaker skill prompt to the LLM and returns a conversational response.
"""

import json
import logging
from collections.abc import Iterator

from langsmith import traceable

from llm_backend import ChatBackend, message_from_history_entry

log = logging.getLogger(__name__)


class Speaker:
    def __init__(self, backend: ChatBackend):
        self._backend = backend

    @staticmethod
    def _build_messages(
        skill_prompt: str,
        instruction: dict,
        history: list[dict] | None,
        rag_context: str | None,
    ) -> list[dict]:
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
        if rag_context and rag_context.strip():
            messages.append({"role": "system", "content": rag_context.strip()})
        if history:
            for msg in history[-10:]:
                messages.append(message_from_history_entry(msg))
        return messages

    @traceable(name="speaker_run", run_type="chain")
    def run(
        self,
        skill_prompt: str,
        instruction: dict,
        history: list[dict] | None = None,
        max_tokens: int = 2000,
        rag_context: str | None = None,
    ) -> str:
        messages = self._build_messages(skill_prompt, instruction, history, rag_context)
        try:
            return self._backend.complete(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )

        except Exception as exc:
            log.warning("Speaker error: %s", exc)
            return (
                "I'm having trouble processing that right now. "
                "Could you try again?"
            )

    @traceable(name="speaker_run_stream", run_type="chain")
    def run_stream(
        self,
        skill_prompt: str,
        instruction: dict,
        history: list[dict] | None = None,
        max_tokens: int = 2000,
        rag_context: str | None = None,
    ) -> Iterator[str]:
        messages = self._build_messages(skill_prompt, instruction, history, rag_context)
        try:
            yield from self._backend.stream_complete(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
        except Exception as exc:
            log.warning("Speaker stream error: %s", exc)
            yield (
                "I'm having trouble processing that right now. "
                "Could you try again?"
            )
