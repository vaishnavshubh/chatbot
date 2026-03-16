"""
Core orchestrator loop.

Implements the pseudocode from md/orchestrator_rules.md:
  Analyze → Validate → Merge → Advance → Speak → Artifacts
"""

import logging
import re
from pathlib import Path

from state import ChatbotState, get_field, set_field
from phase_registry import PhaseRegistry
from analyzer import Analyzer
from speaker import Speaker
from validator import is_valid

log = logging.getLogger(__name__)

# ── Map analyzer output keys → state dotted paths ──────────────────────
FIELD_PATH_MAP: dict[str, str] = {
    # Phase 0
    "consent_acknowledged": "consent_acknowledged",
    "output_preference": "output_preference",
    # Phase 1 (analyzer returns short names)
    "life_stage": "profile.life_stage",
    "pay_type": "profile.pay_type",
    "pay_frequency": "profile.pay_frequency",
    "income_range": "profile.income_range",
    # Phase 2
    "primary_goal": "goal.primary_goal",
    "time_horizon": "goal.time_horizon",
    # Phase 3 — dotted keys (already correct)
    "budget.fixed_expenses": "budget.fixed_expenses",
    "budget.variable_expenses": "budget.variable_expenses",
    "credit.apr": "credit.apr",
    "credit.balance": "credit.balance",
    "credit.minimum_payment": "credit.minimum_payment",
    "credit.due_date": "credit.due_date",
    "retirement.employer_match": "retirement.employer_match",
    "retirement.contribution_rate": "retirement.contribution_rate",
    "loan.principal": "loan.principal",
    "loan.interest_rate": "loan.interest_rate",
    "loan.payment_amount": "loan.payment_amount",
    # Phase 3 — short-name fallbacks
    "fixed_expenses": "budget.fixed_expenses",
    "variable_expenses": "budget.variable_expenses",
    "apr": "credit.apr",
    "balance": "credit.balance",
    "minimum_payment": "credit.minimum_payment",
    "due_date": "credit.due_date",
    "employer_match": "retirement.employer_match",
    "contribution_rate": "retirement.contribution_rate",
    "principal": "loan.principal",
    "interest_rate": "loan.interest_rate",
    "payment_amount": "loan.payment_amount",
    # Phase 5
    "selected_next_action": "selected_next_action",
    "plan_generated": "plan_generated",
}

# Analyzer keys that are control signals, not state fields
_CONTROL_KEYS = {
    "skip_evidence",
    "regenerate_requested",
    "artifact_requested",
    "another_session_requested",
    "session_complete",
    "goal_change_requested",
}

# Product-recommendation guard patterns
_PRODUCT_PATTERNS = [
    re.compile(
        r"\b(Chase|Amex|American Express|Citi|Capital One|Discover|"
        r"Wells Fargo|Vanguard|Fidelity|Schwab|Robinhood|SoFi|"
        r"Betterment|Wealthfront)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byou should invest in\b", re.IGNORECASE),
    re.compile(r"\bI recommend\b", re.IGNORECASE),
    re.compile(r"\bthe best (card|fund|stock|account) is\b", re.IGNORECASE),
]


class SkillLoader:
    """Reads .md skill files from the md/ directory."""

    def __init__(self, md_dir: Path):
        self.md_dir = md_dir

    def load(self, skill_path: str) -> str:
        full_path = self.md_dir / skill_path
        return full_path.read_text(encoding="utf-8")


class Orchestrator:
    def __init__(
        self,
        registry: PhaseRegistry,
        analyzer: Analyzer,
        speaker: Speaker,
        skill_loader: SkillLoader,
    ):
        self.registry = registry
        self.analyzer = analyzer
        self.speaker = speaker
        self.skill_loader = skill_loader

    # ── Public API ──────────────────────────────────────────────────────

    def generate_opening(self, state: ChatbotState) -> str:
        """Produce the Phase 0 welcome message (no user input yet)."""
        phase = self.registry.get_phase(0)
        skill = self.skill_loader.load(phase["skills"]["speaker"])
        missing = self.registry.get_missing_fields(0, state)
        payload = self._build_payload(phase, state, missing)
        payload["instruction"] = (
            "This is the very start of a new conversation. "
            "Deliver the full welcome message as described in your Behavior Rules."
        )
        return self.speaker.run(skill, payload)

    def handle_message(
        self,
        user_message: str,
        state: ChatbotState,
        history: list[dict],
    ) -> tuple[str, ChatbotState, dict]:
        """Process one user turn and return (response, updated_state, artifacts)."""

        phase = self.registry.get_phase(state.current_phase)

        # ── 1. Analyze ──────────────────────────────────────────────
        analyzer_skill = self.skill_loader.load(phase["skills"]["analyzer"])
        extracted = self.analyzer.run(user_message, analyzer_skill, state)
        log.info("Phase %d extracted: %s", state.current_phase, extracted)

        # ── 2. Validate & merge ─────────────────────────────────────
        for key, value in extracted.items():
            if key in _CONTROL_KEYS:
                if key == "skip_evidence" and value:
                    state.evidence_skipped = True
                continue

            field_path = FIELD_PATH_MAP.get(key)
            if field_path is None:
                log.debug("Unknown extracted key: %s", key)
                continue

            if is_valid(field_path, value):
                set_field(state, field_path, value)
            else:
                log.debug("Rejected %s = %r", field_path, value)

        # ── 3. Increment turn counter ───────────────────────────────
        state.phase_turns += 1

        # ── 4. Max-turn guard ───────────────────────────────────────
        max_turns = phase.get("max_turns", 10)
        force_advance = state.phase_turns > max_turns

        # ── 5. Check phase advancement ──────────────────────────────
        advanced = False
        if state.current_phase < 5:
            can = self.registry.can_advance(state.current_phase, state)
            if can or force_advance:
                state.current_phase += 1
                state.phase_turns = 0
                advanced = True
                phase = self.registry.get_phase(state.current_phase)

        # ── 6. Phase 4 auto-generation ──────────────────────────────
        if state.current_phase == 4 and not state.plan_generated:
            return self._generate_plan(state, phase, history)

        # ── 7. Build speaker response ───────────────────────────────
        missing = self.registry.get_missing_fields(state.current_phase, state)
        payload = self._build_payload(phase, state, missing)
        speaker_skill = self.skill_loader.load(phase["skills"]["speaker"])
        response = self.speaker.run(speaker_skill, payload, history)
        response = self._safety_check(response)

        # ── 8. Artifacts ────────────────────────────────────────────
        artifacts = self._check_artifacts(state) if state.plan_generated else {}

        return response, state, artifacts

    # ── Private helpers ─────────────────────────────────────────────────

    def _generate_plan(
        self,
        state: ChatbotState,
        phase: dict,
        history: list[dict],
    ) -> tuple[str, ChatbotState, dict]:
        """Auto-generate the educational plan when entering Phase 4."""
        speaker_skill = self.skill_loader.load(phase["skills"]["speaker"])
        payload = self._build_payload(phase, state, [])
        payload["instruction"] = (
            "Generate the full educational plan now. "
            "Include all five sections: Situation Summary, Key Concepts, "
            "Step-by-Step Checklist, Risks & Pitfalls, and 30-Day Action Plan."
        )
        if state.evidence_skipped:
            payload["instruction"] += (
                " Evidence was skipped — note that the plan is general "
                "and would benefit from revisiting with actual numbers."
            )

        response = self.speaker.run(speaker_skill, payload, history, max_tokens=4000)
        response = self._safety_check(response)
        state.plan_generated = True

        artifacts = self._check_artifacts(state)
        return response, state, artifacts

    def _build_payload(
        self,
        phase: dict,
        state: ChatbotState,
        missing: list[str],
    ) -> dict:
        populated = [
            path for path in set(FIELD_PATH_MAP.values())
            if get_field(state, path) not in (None, False)
        ]
        return {
            "current_phase": state.current_phase,
            "phase_display_name": phase["display_name"],
            "phase_goal": phase["goal"],
            "populated_fields": sorted(populated),
            "missing_fields": missing,
            "state_snapshot": state.model_dump(),
        }

    @staticmethod
    def _safety_check(response: str) -> str:
        for pattern in _PRODUCT_PATTERNS:
            response = pattern.sub("[redacted]", response)
        return response

    @staticmethod
    def _check_artifacts(state: ChatbotState) -> dict:
        artifacts: dict = {}
        if state.output_preference == "pdf" and not state.artifacts.pdf_generated:
            artifacts["pdf_requested"] = True
        return artifacts
