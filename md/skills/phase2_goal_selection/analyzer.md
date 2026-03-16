# Analyzer — Phase 2: Goal Selection

## Purpose

Extract two structured facts from the user's message:
1. The primary financial topic the user wants to explore.
2. The user's planning time horizon.

---

## Input

The user's raw message text and the current conversation state (including profile data from Phase 1).

## Output

Return a JSON object with only the fields that can be confidently extracted.

```json
{
  "primary_goal": "credit_management",
  "time_horizon": "short_term"
}
```

---

## Extraction Rules

### primary_goal (string enum)

The financial topic the user wants to focus on during this session.

| Value | User signals |
|---|---|
| `"financial_foundations"` | "I want to learn the basics", "how to manage my money", "emergency fund", "net worth", "financial goals", "where do I even start" |
| `"budget_cashflow"` | "Budgeting", "I need a budget", "spending", "cash flow", "where does my money go", "50/30/20", "saving money" |
| `"credit_management"` | "Credit", "credit score", "credit card", "APR", "credit report", "building credit", "paying off my card" |
| `"workplace_401k"` | "401k", "401(k)", "retirement", "employer match", "retirement savings", "should I contribute", "company retirement plan" |
| `"student_loans"` | "Student loans", "loan repayment", "federal loans", "loan forgiveness", "student debt", "paying off loans", "PSLF" |
| `"borrowing_basics"` | "Loans", "borrowing", "interest rates", "debt-to-income", "personal loan", "auto loan", "mortgage basics", "how loans work" |

**Disambiguation rules:**
- If the user says "loans" without specifying, check context. If they mention school/college/university, use `"student_loans"`. Otherwise, use `"borrowing_basics"`.
- If the user says "retirement" or "401k", use `"workplace_401k"`.
- If the user says "saving" in the context of building a safety net, use `"financial_foundations"`. If "saving" relates to tracking spending, use `"budget_cashflow"`.
- If the user mentions multiple topics, extract only the one they emphasize most. If ambiguous, omit and let the speaker ask for clarification.

### time_horizon (string enum)

The user's planning timeline.

| Value | Definition | User signals |
|---|---|---|
| `"short_term"` | Less than 6 months | "Right now", "this month", "immediately", "the next few months", "ASAP" |
| `"medium_term"` | 6–24 months | "Next year", "over the coming year", "in the next year or two", "within a year" |
| `"long_term"` | 2+ years | "Long-term", "for the future", "retirement", "in a few years", "building over time" |

**Inference rules:**
- If the user selects `"workplace_401k"` and doesn't mention a time horizon, do NOT auto-set to `"long_term"` — let the speaker ask.
- If the user says "I need to fix this soon" → `"short_term"`.
- If the user says "I'm thinking about the big picture" → `"long_term"`.

---

## Multi-Fact Extraction

Users may state both facts at once.

**Example:** "I want to learn about budgeting so I can get my spending under control in the next couple months."

Extract:
```json
{
  "primary_goal": "budget_cashflow",
  "time_horizon": "short_term"
}
```

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User says "I'm not sure what to focus on" | Return empty `{}` — the speaker should help them choose |
| User asks about a topic outside the six goals | Return empty `{}` — the speaker redirects to supported topics |
| User mentions two goals equally | Return empty `{}` — the speaker asks which one to prioritize |
| User says "all of them" | Return empty `{}` — the speaker explains the one-topic-per-session model |
| User's goal is implied by their profile | Do NOT infer a goal from profile alone; it must come from the user's stated interest |

---

## Validation Contract

The orchestrator will reject:
- `primary_goal` values not in `["financial_foundations", "budget_cashflow", "credit_management", "workplace_401k", "student_loans", "borrowing_basics"]`
- `time_horizon` values not in `["short_term", "medium_term", "long_term"]`

Only extract what is clearly stated or strongly implied. When in doubt, omit the field.
