"""
Pydantic state models for the financial literacy chatbot.
Mirrors the structure defined in md/state_schema.json.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class Profile(BaseModel):
    life_stage: Optional[Literal[
        "student", "new_graduate", "early_career", "career_changer"
    ]] = None
    pay_type: Optional[Literal[
        "salaried", "hourly", "freelance", "stipend"
    ]] = None
    pay_frequency: Optional[Literal[
        "weekly", "biweekly", "semi_monthly", "monthly"
    ]] = None
    income_range: Optional[Literal[
        "under_25k", "25k_50k", "50k_75k", "75k_100k", "over_100k"
    ]] = None


class Goal(BaseModel):
    primary_goal: Optional[Literal[
        "financial_foundations", "budget_cashflow", "credit_management",
        "workplace_401k", "student_loans", "borrowing_basics"
    ]] = None
    time_horizon: Optional[Literal[
        "short_term", "medium_term", "long_term"
    ]] = None


class Budget(BaseModel):
    fixed_expenses: Optional[float] = Field(None, ge=0)
    variable_expenses: Optional[float] = Field(None, ge=0)


class Credit(BaseModel):
    apr: Optional[float] = Field(None, ge=0, le=100)
    balance: Optional[float] = Field(None, ge=0)
    minimum_payment: Optional[float] = Field(None, ge=0)
    due_date: Optional[str] = None


class Retirement(BaseModel):
    employer_match: Optional[str] = None
    contribution_rate: Optional[float] = Field(None, ge=0, le=100)


class Loan(BaseModel):
    principal: Optional[float] = Field(None, ge=0)
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    payment_amount: Optional[float] = Field(None, ge=0)


class Artifacts(BaseModel):
    pdf_generated: bool = False


class ChatbotState(BaseModel):
    session_id: Optional[str] = None
    current_phase: int = Field(0, ge=0, le=5)
    consent_acknowledged: bool = False
    output_preference: Optional[Literal["chat", "pdf", "csv", "charts"]] = None
    profile: Profile = Field(default_factory=Profile)
    goal: Goal = Field(default_factory=Goal)
    budget: Budget = Field(default_factory=Budget)
    credit: Credit = Field(default_factory=Credit)
    retirement: Retirement = Field(default_factory=Retirement)
    loan: Loan = Field(default_factory=Loan)
    plan_generated: bool = False
    selected_next_action: Optional[str] = None
    artifacts: Artifacts = Field(default_factory=Artifacts)
    evidence_skipped: bool = False
    phase_turns: int = 0


def get_field(state: ChatbotState, path: str):
    """Retrieve a nested field value using a dotted path like 'profile.life_stage'."""
    parts = path.split(".")
    obj = state
    for part in parts:
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


def set_field(state: ChatbotState, path: str, value) -> ChatbotState:
    """Set a nested field value using a dotted path like 'profile.life_stage'."""
    parts = path.split(".")
    if len(parts) == 1:
        setattr(state, parts[0], value)
    elif len(parts) == 2:
        nested = getattr(state, parts[0])
        setattr(nested, parts[1], value)
    return state
