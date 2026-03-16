# Analyzer — Phase 4: Plan Generation

## Purpose

Phase 4 is primarily a generation phase, not an extraction phase. The analyzer's role here is minimal: confirm that the plan has been delivered and detect any user feedback or corrections.

---

## Input

The user's raw message text (typically a response to the generated plan) and the current conversation state.

## Output

Return a JSON object signaling plan status and any corrections.

```json
{
  "plan_generated": true
}
```

---

## Extraction Rules

### plan_generated (boolean)

This field is set by the **orchestrator**, not extracted from the user. The orchestrator sets `plan_generated = true` once the speaker has delivered the complete plan. The analyzer does not need to extract this field.

### User Corrections

After the plan is delivered, the user may request corrections. The analyzer should detect:

| User signal | Extraction |
|---|---|
| "Actually, my balance is $4,000, not $3,500" | `{"credit.balance": 4000}` |
| "I forgot to mention my rent is $1,300" | `{"budget.fixed_expenses": 1300}` (or adjustment) |
| "That looks great" / "Thanks" | `{}` (no corrections needed) |
| "Can you regenerate with the new numbers?" | `{"regenerate_requested": true}` |

### Regeneration Handling

If the user provides corrections and asks for a new plan:
1. Extract the corrected values.
2. Set `"regenerate_requested": true`.
3. The orchestrator will update state with corrections, reset `plan_generated = false`, and re-trigger plan generation.

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User asks a follow-up question about a concept in the plan | Return `{}` — the speaker handles educational Q&A within Phase 4 |
| User says "Can I get the PDF now?" | Return `{"artifact_requested": "pdf"}` |
| User wants to change their goal entirely | Return `{"goal_change_requested": true}` — the orchestrator decides how to handle this |
| User says "Looks good, what's next?" | Return `{}` — the orchestrator advances to Phase 5 |

---

## Validation Contract

The orchestrator will:
- Only accept `plan_generated` as a boolean
- Validate any corrected evidence fields against the same rules as Phase 3
- Handle `regenerate_requested` by re-entering Phase 4 generation

This analyzer is intentionally lightweight. Most Phase 4 logic lives in the orchestrator and speaker.
