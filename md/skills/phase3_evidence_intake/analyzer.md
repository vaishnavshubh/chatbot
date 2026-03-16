# Analyzer — Phase 3: Evidence Intake

## Purpose

Extract financial numbers and evidence from the user's message or uploaded documents. The fields to extract depend on the user's selected `primary_goal`.

---

## Input

The user's raw message text (or document content) and the current conversation state, including `goal.primary_goal`.

## Output

Return a JSON object with only the fields that can be confidently extracted. Field names must match the state schema paths.

```json
{
  "budget.fixed_expenses": 1800,
  "budget.variable_expenses": 650
}
```

---

## Goal-Specific Extraction Rules

### When primary_goal == "budget_cashflow"

| Field | Type | Description | User signals |
|---|---|---|---|
| `budget.fixed_expenses` | number | Total monthly fixed expenses in USD | "My rent is $1200, utilities are $150, and I pay $50 for subscriptions" → sum to 1400 |
| `budget.variable_expenses` | number | Total monthly variable expenses in USD | "I spend about $400 on food and $200 on going out" → sum to 600 |

**Summation rule:** If the user lists individual expenses, sum them into the total for each category. Fixed expenses include: rent/mortgage, utilities, insurance, subscriptions, car payment, minimum debt payments. Variable expenses include: groceries, dining out, entertainment, transportation, clothing, personal care.

### When primary_goal == "credit_management"

| Field | Type | Description | User signals |
|---|---|---|---|
| `credit.apr` | number | Annual percentage rate (e.g., 22.99) | "My APR is 22.99%", "interest rate is about 23%" |
| `credit.balance` | number | Current outstanding balance in USD | "I owe about $3,500", "my balance is $3500" |
| `credit.minimum_payment` | number | Minimum monthly payment in USD | "Minimum payment is $75", "I pay at least $75 a month" |
| `credit.due_date` | string | Payment due date | "Due on the 15th", "I pay on the 1st of each month" |

### When primary_goal == "workplace_401k"

| Field | Type | Description | User signals |
|---|---|---|---|
| `retirement.employer_match` | string | Employer match formula or percentage | "My company matches 100% up to 6%", "they match 50 cents on the dollar up to 4%", "3% match" |
| `retirement.contribution_rate` | number | Employee contribution rate as a percentage | "I'm contributing 4%", "I put in 6% of my salary" |

**Match formula note:** Employer match descriptions vary widely. Store the user's description as-is if it includes a formula (e.g., "100% up to 6%"). If the user gives only a percentage (e.g., "3%"), store "3%".

### When primary_goal == "student_loans"

| Field | Type | Description | User signals |
|---|---|---|---|
| `loan.principal` | number | Outstanding loan balance in USD | "I owe $35,000 in student loans", "my balance is $28k" |
| `loan.interest_rate` | number | Annual interest rate as a percentage | "5.5% interest", "my rate is 4.99%" |
| `loan.payment_amount` | number | Current monthly payment in USD | "I pay $350 a month", "my payment is $400" |

### When primary_goal == "financial_foundations" or "borrowing_basics"

These goals have no required numeric fields. The analyzer should still attempt to extract any numbers the user volunteers, storing them in the appropriate state category. If no numbers are present, return `{}`.

---

## Document Upload Handling

If the user uploads a document (pay stub, credit card statement, loan statement, 401(k) summary), extract all recognizable fields from the document content.

**Common document types and what to extract:**

| Document type | Fields to extract |
|---|---|
| Credit card statement | `credit.apr`, `credit.balance`, `credit.minimum_payment`, `credit.due_date` |
| Pay stub | `profile.pay_frequency` (if not already set), income estimate |
| 401(k) summary | `retirement.employer_match`, `retirement.contribution_rate` |
| Student loan statement | `loan.principal`, `loan.interest_rate`, `loan.payment_amount` |

---

## Numeric Parsing Rules

- Strip currency symbols: "$3,500" → 3500
- Strip commas: "3,500" → 3500
- Handle "k" shorthand: "35k" → 35000
- Percentages: "22.99%" → 22.99 (store as the number, not the string)
- Ranges: "between $300 and $400" → use the midpoint (350) or omit and ask for clarification

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User says "I don't know my APR" | Return empty for that field — the speaker will explain how to find it or offer to skip |
| User gives a range ("around $1500–$2000") | Use the midpoint ($1750) if reasonable, or omit and let the speaker clarify |
| User provides numbers for a different goal category | Extract and store them in the correct state path (out-of-phase storage is allowed by the orchestrator) |
| User says "let me check and come back" | Return `{}` — the speaker will offer to continue or wait |
| User says "skip" or "I'd rather not share" | Return `{"skip_evidence": true}` — the orchestrator handles the skip |

---

## Validation Contract

The orchestrator will reject:
- Negative numbers for any financial field
- `credit.apr` values above 100
- `loan.interest_rate` values above 100
- `retirement.contribution_rate` values above 100
- Non-numeric values where numbers are expected

Only extract what is clearly stated or can be reliably parsed. When in doubt, omit the field.
