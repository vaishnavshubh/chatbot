"""
Validates analyzer-extracted values against the constraints
defined in state_schema.json before they are merged into state.
"""

ENUM_VALIDATORS: dict[str, list[str]] = {
    "output_preference": ["chat", "pdf", "csv", "charts"],
    "profile.life_stage": ["student", "new_graduate", "early_career", "career_changer"],
    "profile.pay_type": ["salaried", "hourly", "freelance", "stipend"],
    "profile.pay_frequency": ["weekly", "biweekly", "semi_monthly", "monthly"],
    "profile.income_range": [
        "under_25k", "25k_50k", "50k_75k", "75k_100k", "over_100k",
    ],
    "goal.primary_goal": [
        "financial_foundations", "budget_cashflow", "credit_management",
        "workplace_401k", "student_loans", "borrowing_basics",
    ],
    "goal.time_horizon": ["short_term", "medium_term", "long_term"],
}

# (min, max) — None means unbounded
NUMERIC_FIELDS: dict[str, tuple[float | None, float | None]] = {
    "budget.fixed_expenses": (0, None),
    "budget.variable_expenses": (0, None),
    "credit.apr": (0, 100),
    "credit.balance": (0, None),
    "credit.minimum_payment": (0, None),
    "retirement.contribution_rate": (0, 100),
    "loan.principal": (0, None),
    "loan.interest_rate": (0, 100),
    "loan.payment_amount": (0, None),
}

BOOLEAN_FIELDS = {"consent_acknowledged", "plan_generated"}

STRING_FIELDS = {"credit.due_date", "retirement.employer_match", "selected_next_action"}


def is_valid(field_path: str, value) -> bool:
    """Return True if *value* is acceptable for *field_path*."""
    if field_path in BOOLEAN_FIELDS:
        return isinstance(value, bool)

    if field_path in ENUM_VALIDATORS:
        return value in ENUM_VALIDATORS[field_path]

    if field_path in NUMERIC_FIELDS:
        if not isinstance(value, (int, float)):
            return False
        lo, hi = NUMERIC_FIELDS[field_path]
        if lo is not None and value < lo:
            return False
        if hi is not None and value > hi:
            return False
        return True

    if field_path in STRING_FIELDS:
        return isinstance(value, str) and len(value.strip()) > 0

    return False
