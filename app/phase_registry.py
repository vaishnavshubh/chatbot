"""
Loads phase_registry.json and provides phase lookup, field resolution,
and advancement logic.
"""

import json
from pathlib import Path

from state import ChatbotState, get_field


class PhaseRegistry:
    def __init__(self, registry_path: Path):
        with open(registry_path) as f:
            data = json.load(f)
        self.phases = {p["id"]: p for p in data["phases"]}

    def get_phase(self, phase_id: int) -> dict:
        return self.phases[phase_id]

    def get_missing_fields(self, phase_id: int, state: ChatbotState) -> list[str]:
        if phase_id == 0:
            missing = []
            if not state.consent_acknowledged:
                missing.append("consent_acknowledged")
            if state.output_preference is None:
                missing.append("output_preference")
            return missing

        if phase_id == 1:
            fields = [
                "profile.life_stage", "profile.pay_type",
                "profile.pay_frequency", "profile.income_range",
            ]
            return [f for f in fields if get_field(state, f) is None]

        if phase_id == 2:
            fields = ["goal.primary_goal", "goal.time_horizon"]
            return [f for f in fields if get_field(state, f) is None]

        if phase_id == 3:
            goal = state.goal.primary_goal
            required = (
                self.phases[3]
                .get("required_fields_by_goal", {})
                .get(goal, [])
            )
            return [f for f in required if get_field(state, f) is None]

        if phase_id == 4:
            return [] if state.plan_generated else ["plan_generated"]

        if phase_id == 5:
            return [] if state.selected_next_action else ["selected_next_action"]

        return []

    def can_advance(self, phase_id: int, state: ChatbotState) -> bool:
        if phase_id == 0:
            return (
                state.consent_acknowledged
                and state.output_preference is not None
            )

        if phase_id == 1:
            p = state.profile
            return all([p.life_stage, p.pay_type, p.pay_frequency, p.income_range])

        if phase_id == 2:
            return (
                state.goal.primary_goal is not None
                and state.goal.time_horizon is not None
            )

        if phase_id == 3:
            if state.evidence_skipped:
                return True
            goal = state.goal.primary_goal
            required = (
                self.phases[3]
                .get("required_fields_by_goal", {})
                .get(goal, [])
            )
            if not required:
                # Qualitative goals still need at least one turn of conversation
                return state.phase_turns > 0
            return all(get_field(state, f) is not None for f in required)

        if phase_id == 4:
            return state.plan_generated

        if phase_id == 5:
            return state.selected_next_action is not None

        return False
