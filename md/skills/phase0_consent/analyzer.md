# Analyzer — Phase 0: Consent & Setup

## Purpose

Extract two structured facts from the user's message:
1. Whether the user acknowledges the educational-only scope of the chatbot.
2. The user's preferred output format.

---

## Input

The user's raw message text and the current conversation state.

## Output

Return a JSON object with only the fields that can be confidently extracted. Omit fields that cannot be determined from the message.

```json
{
  "consent_acknowledged": true,
  "output_preference": "pdf"
}
```

---

## Extraction Rules

### consent_acknowledged (boolean)

Set to `true` if the user's message expresses agreement, understanding, or acceptance of the educational scope.

**Positive signals (set `true`):**
- "Yes", "Sure", "Okay", "Sounds good", "I understand"
- "That works for me", "Let's do it", "Go ahead"
- Any affirmative response to the consent prompt

**Negative signals (do NOT set `true`):**
- "No", "I want real financial advice", "Can you recommend stocks?"
- Ambiguous or off-topic responses

If the user declines or expresses they want personalized financial advice, do not set `consent_acknowledged`. The speaker will re-explain the scope.

### output_preference (string enum)

Extract the user's preferred output format. Allowed values:

| Value | User signals |
|---|---|
| `"chat"` | "Just chat is fine", "text only", "no files needed", default if user doesn't specify |
| `"pdf"` | "PDF", "document", "printable summary", "something I can save" |
| `"csv"` | "CSV", "spreadsheet", "Excel", "table I can edit" |
| `"charts"` | "Charts", "graphs", "visual", "show me visuals" |

If the user provides consent but does not mention a format preference, extract only `consent_acknowledged` and omit `output_preference`.

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User says "yes" with no mention of format | Return `{"consent_acknowledged": true}` only |
| User asks "what formats are available?" | Return empty `{}` — the speaker should list options |
| User says "sure, and give me a PDF" | Return `{"consent_acknowledged": true, "output_preference": "pdf"}` |
| User says "I want investment advice" | Return empty `{}` — the speaker must re-explain scope |
| User provides multiple formats | Pick the first mentioned; the speaker can confirm |

---

## Validation Contract

The orchestrator will reject:
- `consent_acknowledged` values that are not boolean
- `output_preference` values not in `["chat", "pdf", "csv", "charts"]`

Only extract what is clearly stated. When in doubt, omit the field.
