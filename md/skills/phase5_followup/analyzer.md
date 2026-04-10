# Analyzer — Phase 5: Follow-up

## Purpose

Extract the user's committed next action from their message. This is the final extraction in the conversation.

---

## Input

The user's raw message text and the current conversation state (plan already generated).

## Output

Return a JSON object with the extracted action.

```json
{
  "selected_next_action": "Review my credit card statement tonight and set up autopay for the minimum"
}
```

---

## Extraction Rules

### selected_next_action (string)

A concrete, specific action the user commits to taking in the near future (ideally within 48 hours).

**Strong signals (extract as-is or lightly cleaned up):**

| User says | Extracted value |
|---|---|
| "I'll check my credit score tonight" | "Check my credit score tonight" |
| "I'm going to set up autopay this weekend" | "Set up autopay this weekend" |
| "I'll review my 401k enrollment on Monday" | "Review 401k enrollment on Monday" |
| "I want to create a budget spreadsheet" | "Create a budget spreadsheet" |
| "I'll look into my student loan repayment options" | "Research student loan repayment options" |

**Cleaning rules:**
- Remove filler words ("I think I'll" → just the action)
- Capitalize the first letter
- Keep the time reference if the user includes one ("tonight", "this week")
- Keep it concise — one sentence maximum

**Weak signals (do NOT extract — ask for specificity):**

| User says | Why it's too vague |
|---|---|
| "I'll think about it" | No concrete action |
| "Maybe" | Non-committal |
| "I'll try to be better with money" | Not specific or time-bound |
| "Sounds good" | Acknowledgment, not a commitment |

If the user's response is vague, return `{}` so the speaker can ask for something more specific.

---

## Additional Signals

| User signal | Extraction |
|---|---|
| "Can we do another topic?" | `{"another_session_requested": true}` |
| "I'm done, thanks" | `{"session_complete": true}` — the speaker delivers a closing message |
| "Can I get the PDF?" | Return `{}` — the speaker explains the plan is available in the chat history |

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User commits to multiple actions | Extract the first/primary one as `selected_next_action` |
| User asks a new question about the plan | Return `{}` — the speaker answers within Phase 5 |
| User provides a very long action description | Summarize to one clear sentence |
| User says they already took an action | Extract it: "Already checked my credit score today" |

---

## Validation Contract

The orchestrator will:
- Accept any non-empty string for `selected_next_action`
- Reject empty strings or null values
- Treat this field as the session's final required extraction
