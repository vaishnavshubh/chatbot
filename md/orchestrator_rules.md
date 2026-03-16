# Orchestrator Rules

The orchestrator enforces deterministic conversation flow.

## Phase Transitions
A phase may only complete if all required fields in phase_registry.json are populated.

## Missing Information
If required fields are missing, the speaker must ask targeted questions.

## Goal-Specific Evidence

Budget
- fixed_expenses
- variable_expenses

Credit
- apr
- balance
- minimum_payment

401k
- employer_match
- contribution_rate

Loan
- principal
- interest_rate
- payment_amount

## Safety Rules

The chatbot must NOT:
- recommend specific stocks
- recommend financial products
- provide tax advice
- provide legal advice

Instead, the bot explains financial decision frameworks.

## Artifact Generation

Artifacts may be generated only after Phase 4.

Possible artifacts:
- PDF summary
- CSV budget
- charts