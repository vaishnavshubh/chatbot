# Skill 8: Error Recovery and Graceful Degradation

## Purpose

This skill is the canonical reference for configuring how the system handles failures — from malformed Analyzer output to LLM outages to users who go off the rails. Every component can fail. The question isn't whether failures happen, but whether the conversation survives them gracefully.

Error recovery behavior is domain-sensitive. A medical triage bot must terminate quickly on repeated failures (safety-critical). A casual coaching bot can keep stumbling forward with fallback messages. This skill defines the error catalog, recovery strategies, and the configuration points where domain authors tune the behavior.

---

## Core Principles

1. **The conversation must survive.** No single failure should kill a conversation. Every error has a fallback that keeps the user engaged, even if the system operates in a degraded mode temporarily.
2. **Fail safe, not fail silent.** Every error is logged with enough context to diagnose later. But the user never sees stack traces, field names, or error codes. They see a natural continuation of the conversation.
3. **Retry before fallback, fallback before termination.** The escalation ladder is always: retry → degrade → fallback → terminate. Most errors are resolved at the retry level and the user never notices.
4. **Errors are attributable.** Every error log identifies which component failed (Analyzer, Orchestrator, Speaker, LLM, infrastructure), what the input was, what went wrong, and what recovery action was taken.
5. **Recovery preserves state integrity.** No recovery action should corrupt state. If recovery can't guarantee state integrity, it should skip the update and let the next turn try again with clean state.

---

## Error Classification

### Severity Levels

| Level | Definition | User Impact | Recovery Expectation |
|-------|-----------|-------------|---------------------|
| **Low** | Suboptimal but functional. Output is usable with minor issues. | None — user doesn't notice | Log and continue |
| **Medium** | Degraded quality. Output is usable but not ideal. | Slightly awkward response | Log, optionally retry once |
| **High** | Component failed to produce usable output. | Noticeable gap in conversation | Retry, then fallback |
| **Critical** | System-level failure affecting multiple components. | Conversation at risk | Immediate fallback, possible termination |

### Component Sources

| Source | Examples |
|--------|---------|
| **Analyzer** | Malformed JSON, hallucinated fields, type mismatches, empty extraction |
| **Speaker** | Leaked field names, asked for collected info, empty output, off-tone |
| **Orchestrator** | State corruption, invalid transition, schema mismatch |
| **LLM** | Timeout, rate limit, API error, content filter triggered |
| **Infrastructure** | Skill file missing, state persistence failure, snapshot failure |

---

## Error Catalog

### Analyzer Errors

| Error | Severity | Recovery |
|-------|----------|----------|
| **Parse failure** — output is not valid JSON | High | Retry with stricter prompt (up to 2 retries). If all fail, return empty delta. |
| **Hallucinated fields** — returned fields not in the phase schema | Low | Strip unknown fields, keep only valid ones. Log for skill refinement. |
| **Type mismatch** — field value doesn't match expected type | Low | Attempt type coercion (e.g., string → integer). If coercion fails, reject the field. State unchanged for that field. |
| **Invalid enum** — value not in the allowed set | Low | Attempt fuzzy match (case-insensitive, substring). If no match, reject the field. Log as potential skill improvement opportunity. |
| **Empty extraction** — no fields extracted from a message that likely contained information | Low | Accept for this turn. Track consecutive empty extractions. After threshold (default 3), escalate to Speaker hint adjustment. |
| **Repeated empty extraction** — multiple consecutive turns with no extraction | Medium | Signal the Speaker to adjust questioning approach — simplify questions, offer specific options, or rephrase. |
| **Low confidence** — extraction confidence below threshold | Low | Accept extraction but route to clarification turn type so the Speaker can verify with the user. |
| **All retries exhausted** — no valid output after all attempts | High | Return empty delta. Speaker proceeds with no new extractions, effectively asking the user to rephrase. |

### Speaker Errors

| Error | Severity | Recovery |
|-------|----------|----------|
| **Empty output** — returned empty or whitespace-only | High | Retry once. If still empty, use turn-type fallback message. |
| **Leaked field name** — output contains internal field names (e.g., `target_company`) | High | Attempt in-place fix (replace underscored names with display names). If the leak is prominent (quoted or emphasized), retry with explicit reminder. |
| **Leaked phase name** — output contains internal phase names (e.g., `interview_setup`) | High | Retry with explicit reminder to avoid phase names. |
| **Leaked JSON** — output contains JSON structures | High | Retry. The Speaker may have confused its role with the Analyzer. |
| **Used "required/optional" language** | Medium | Log for review. Send as-is if the rest is acceptable — awkward but not harmful. |
| **Asked for already-collected information** | Medium | Log for review. May be a false positive from heuristic matching. Send as-is unless confirmed. |
| **Excessive length** — output over 500 words | Low | Log. If extremely long, truncate at a sentence boundary. |
| **Fallback used** — Speaker failed after all retries | High | Conversation continues with generic fallback message. Log for investigation. |

### Orchestrator Errors

| Error | Severity | Recovery |
|-------|----------|----------|
| **State corruption** — integrity check failed after update | Critical | Rollback to last snapshot. Re-run the turn with clean state. If rollback fails, terminate with apology. |
| **Invalid transition** — attempted transition to non-existent or disallowed phase | Medium | Reject transition. Stay in current phase. Log the invalid target. |
| **Schema mismatch** — state schema doesn't match expected structure | High | Attempt to continue with available fields. If critical fields are missing, terminate. Likely a deployment issue. |
| **Completion calculation error** — phase completion check failed | Medium | Default to `required_complete: false` (safe side). Conversation continues but may not auto-advance. |

### LLM Errors

| Error | Severity | Recovery |
|-------|----------|----------|
| **Timeout** — call exceeded timeout | High | Retry once with same prompt. If still times out, use component-specific fallback. |
| **Rate limit** — API returned rate limit error | High | Wait for retry-after duration (capped at 30s), then retry once. If still limited, use fallback. |
| **API error** — non-retryable error | High | Use component-specific fallback. Log full error. |
| **Content filter** — LLM refused to process | Medium | For Analyzer: return empty delta. For Speaker: use fallback message. Log the triggering input. |
| **Model unavailable** — configured model is down | Critical | Attempt fallback model if configured. Otherwise terminate with apology. |

### Infrastructure Errors

| Error | Severity | Recovery |
|-------|----------|----------|
| **Skill file missing** — phase's analyzer.md or speaker.md not found | Critical | Cannot continue in this phase. If another phase is reachable, transition. Otherwise terminate. |
| **State persistence failure** — failed to persist state to storage | Medium | Continue in-memory. Retry persistence next turn. Resumption won't work if the process crashes. |
| **Snapshot failure** — failed to save state snapshot before mutation | Medium | Continue without snapshot. Rollback capability is lost for this turn. |

---

## Recovery Decision Matrix

Quick reference for the most common failures:

| Failure | Retry? | Fallback | State Impact | User Sees |
|---------|--------|----------|-------------|-----------|
| Analyzer: no JSON | Yes (2x) | Empty delta | None | Normal follow-up |
| Analyzer: invalid fields | No | Drop invalid, keep valid | Valid only | Normal response |
| Analyzer: empty extraction | No | Track streak | None | Follow-up (maybe rephrased) |
| Speaker: empty output | Yes (1x) | Generic fallback | None | Generic but usable |
| Speaker: leaked internals | Fix or retry (1x) | Auto-fix if possible | None | Fixed or retried |
| Speaker: re-asked collected | Log only | Send as-is | None | Slightly redundant |
| LLM: timeout | Yes (1x) | Component fallback | None | Delayed or generic |
| LLM: rate limit | Wait + retry | Component fallback | None | Delayed |
| LLM: unavailable | Model fallback | Terminate if none | None | Delayed, generic, or ended |
| State: corruption | Rollback | Terminate if no snapshot | Rolled back | Normal (may re-ask) |

---

## User Behavior Recovery

Not all "errors" come from the system. Users also produce situations that need recovery.

### Off-Topic Behavior

When the Analyzer returns empty extractions for multiple consecutive turns, the user may be going off-topic.

**Escalation:**
1. **1–2 empty turns:** Normal — the user might be chatting, asking questions, or saying "ok." No special action.
2. **3 empty turns (configurable threshold):** Signal the Speaker to gently redirect. Hint: "The user has been off-topic. Gently redirect to the current phase."
3. **6+ empty turns:** Signal the Speaker to be more direct. Hint: "The user has been off-topic for many turns. Directly but politely redirect."

Reset the counter whenever the Analyzer extracts something.

### Refusal to Provide Information

When a user declines to answer a specific question ("I'd rather not say"), track refusals per field.

**Escalation:**
1. **First refusal:** Speaker explains why the information helps (guided by the phase's speaker.md).
2. **Second refusal (configurable threshold):** If the field is marked as skippable in the schema, move on. If required and not skippable, the Speaker acknowledges the user's preference and tries a different approach.
3. **Persistent refusal on required field:** The phase cannot complete. The Orchestrator may need to offer an alternative path or explain that the information is necessary to proceed.

Reset refusal tracking when the phase changes.

### Contradictions and Corrections

When the Analyzer extracts a value that conflicts with an existing value (and the field's update policy is `overwrite`), the Orchestrator routes to a clarification turn.

**Escalation:**
1. **First contradiction:** Clarification turn — the Speaker asks naturally which value is correct.
2. **Second clarification attempt (configurable):** If the user hasn't resolved it, force-resolve by accepting the most recent value. Log the conflict.

Reset conflict tracking when the phase changes.

---

## State Integrity

After every state mutation, verify:

1. **Active phase exists** in the phase registry. If not, this is a critical error — the system is pointing to a phase that doesn't exist.
2. **Field types match schema.** For every non-null field in state, verify the value type matches what the schema expects. Type mismatches indicate corruption.
3. **Completion flags match actual data.** Recompute whether required fields are complete from the actual state data and compare to the stored completion flags. Mismatches indicate a completion calculation bug.
4. **Turn counts are sane.** Phase turn count should never exceed total turn count.

If integrity issues are found: warnings are logged and the system continues. High-severity issues trigger a rollback to the last snapshot. Critical issues (like an invalid active phase) trigger termination.

---

## Customization Points

### Fallback Messages

The default fallback messages are generic and domain-neutral. Override them to match your agent's tone and domain:

| Turn Type | Default | Example Override (Medical Intake) |
|---|---|---|
| first_turn | "Hi there! Let's get started. Could you tell me a bit about what you're looking for?" | "Hello, I'm here to help gather some information before your appointment. What brings you in today?" |
| standard | "Thanks for that! Could you tell me a bit more?" | "Thank you. Could you tell me a bit more about what you're experiencing?" |
| phase_transition | "Great, let's move on to the next step." | "Thank you for that information. Now I'd like to ask about your medical history." |
| clarification | "I want to make sure I understand correctly — could you clarify that last point?" | "I want to make sure I have this right — could you help me understand that last detail?" |
| entity_transition | "Got it! Let's talk about the next one — what can you tell me?" | "Thank you. Now I'd like to ask about your next medication — what is it called?" |

### Termination Message

Default: "I apologize, but I've encountered an issue I can't recover from. Please try starting a new conversation."

Override for domains where termination has specific implications — e.g., a medical bot should include guidance on what to do next, not just "start a new conversation."

### Error Tolerance Thresholds

These thresholds determine how aggressively the system escalates. Tune per domain:

| Threshold | Default | Lower For | Raise For |
|---|---|---|---|
| Max Analyzer retries | 2 | Domains where extraction errors are safety-relevant | Domains where retries are cheap and quality matters less |
| Max Speaker retries | 1 | N/A (1 is usually right) | N/A |
| Consecutive component errors before escalation | 3 | Safety-critical domains (1–2) | High-tolerance casual domains (5+) |
| Max errors per turn | 5 | Safety-critical domains | High-tolerance domains |
| Off-topic redirect threshold | 3 turns | Structured intake (2) | Free-form exploration (5+) |
| Max refusals per field | 2 | Strict compliance requirements (1) | Casual optional collection (3+) |
| Max clarification attempts | 2 | N/A | N/A |
| Min extraction confidence | 0.7 | Domains requiring high accuracy (0.85) | Casual domains accepting ambiguity (0.5) |

### Fallback Models

Each component can have a fallback model configured for degraded operation. When the primary model is unavailable or repeatedly failing, the system can switch to the fallback before resorting to termination.

- **Analyzer fallback:** Extraction quality may degrade with a smaller model. Accept the trade-off — degraded extraction is better than no extraction.
- **Speaker fallback:** Response quality degrades but the conversation continues. This is the most important fallback to configure.
- **Summary fallback:** Summary failure is non-critical. If no fallback is available, skip summarization entirely — the conversation can continue with only raw recent turns as history.

Fallback model selection is an implementation concern — model names are set in the implementation config, not in the skills or rules files.

### What Should NEVER Be Customized

- The escalation ladder (retry → degrade → fallback → terminate). Skipping levels creates unpredictable behavior.
- The requirement to log every error. Silent failures are undebuggable.
- State integrity checking after every mutation. Skipping this risks silent corruption.
- The principle that recovery never corrupts state. Only the Orchestrator writes state.

---

## Configuration Reference

| Parameter | Default | Description |
|---|---|---|
| Max Analyzer retries | 2 | Retries on parse failure with progressively stricter prompts |
| Max Speaker retries | 1 | Retries on validation failure with issue-specific feedback |
| Consecutive error threshold | 3 | Consecutive component failures before escalation |
| Max errors per turn | 5 | Total errors across all components in a single turn before escalation |
| Min extraction confidence | 0.7 | Below this, route to clarification turn |
| Off-topic redirect threshold | 3 | Consecutive empty extractions before Speaker gets redirect hint |
| Max refusals per field | 2 | Refusals before skipping (if skippable) or changing approach |
| Max clarification attempts | 2 | Clarification rounds before force-resolving a contradiction |
| Auto-correct enums | true | Whether to attempt fuzzy matching on invalid enum values |
| Termination message | (see above) | Message sent to user when conversation must terminate |
| Alert on critical | true | Whether to alert monitoring on critical errors |

---

## Testing Scenarios

| Scenario | Trigger | Assert |
|----------|---------|--------|
| Analyzer returns prose | Mock: "I think the user means..." | Empty delta, conversation continues |
| Analyzer partial JSON | Mock: truncated JSON | Tolerant parser recovers or retry succeeds |
| All Analyzer retries fail | Mock all bad output | Fallback empty delta, Speaker continues |
| Speaker returns JSON | Mock: `{"response":"..."}` | Detected, retried, fallback used |
| Speaker leaks field name | Mock: "target_company" | In-place fix or retry |
| LLM timeout then success | Mock first timeout | Retry succeeds, user sees normal response |
| LLM fully down | Mock all calls failing | Fallback messages used, conversation survives |
| State corruption | Set invalid active_phase | Rollback to snapshot |
| 3+ empty extractions | Mock empty Analyzer output | Stall detected, Speaker adjusts approach |
| User refuses 3x | Simulate refusals | Tracked, field skipped if skippable |
| Off-topic 4 turns | Simulate off-topic messages | Gentle then firm redirect |
| Contradiction | Mock conflicting values | Clarification turn triggered |
| Escalation chain | Exhaust retries across turns | Escalates through severity levels |
| Turn error limit | 5+ errors in one turn | Forces escalation |

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Catching all exceptions generically | Can't debug specific errors | Use the error catalog with specific classifications |
| Not resetting per-turn tracking | Old errors escalate new turns | Reset turn error count at the start of each turn |
| Not recording successes | Consecutive error counter never resets | Reset consecutive count after each successful step |
| Retrying Speaker with same prompt | Gets same bad output | Append retry suffix with specific issues found |
| Logging without context | Can't trace failures to specific conversations | Include conversation_id, turn number, and phase in every log |
| State writes during recovery | Corruption worsens | Only the Orchestrator writes state, never recovery code |
| No fallback model configured | Primary model down = conversation dead | Configure at least a Speaker fallback in the implementation config |
| Not resetting trackers on phase transition | Old phase counters bleed into new phase | Reset off-topic, refusal, and conflict trackers on phase change |
| Treating every empty extraction as an error | "ok" genuinely has nothing to extract | Only flag after consecutive threshold is reached |
| No integrity check after state mutation | Corruption goes undetected until it causes a visible failure | Check integrity after every state update |
