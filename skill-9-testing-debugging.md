# Skill 9: Testing and Debugging

## Purpose

This skill is the canonical reference for validating, testing, and debugging a multi-phase information-extraction agent. It covers three stages: pre-deployment validation (does the configuration hold together?), functional testing (does the system behave correctly?), and runtime debugging (what went wrong in production?).

Testing strategy varies by domain. A medical intake agent needs rigorous extraction accuracy testing and edge-case coverage. A casual coaching bot can tolerate looser validation. This skill defines the full testing framework and the customization points where domain authors tune the rigor.

---

## Core Principles

1. **Test the seams, not just the parts.** Individual components may work perfectly in isolation but fail when connected. The most critical tests are integration tests that verify the handoffs: Analyzer output → Orchestrator merge → Speaker context.
2. **Validate configuration before runtime.** Most production failures trace back to configuration errors — mismatched field names, missing skill files, unreachable phases. Catch these at build time with deterministic checks (no LLM calls needed).
3. **Make the invisible visible.** The hardest bugs are in the AI's behavior — why did the Analyzer miss that field? Why did the Speaker re-ask? Debugging tools must expose the full prompt, the raw AI output, and the Orchestrator's decisions.
4. **Test with realistic data.** Synthetic "the user says hello" test cases miss the complexity of real conversations. Use realistic, messy, multi-turn scenarios.

---

## Part 1: Pre-Deployment Validation

These checks run before the agent is deployed. They validate the static configuration — no LLM calls needed. All checks are deterministic and fast.

### Check 1: File Completeness

Every phase in the registry must have its skill files present and readable.

**Verify:**
- Every phase has both `skills/{phase_name}/analyzer.md` and `skills/{phase_name}/speaker.md`.
- All three prompt templates exist: `prompts/analyzer_template.md`, `prompts/speaker_template.md`, and `prompts/summary_template.md`.
- All configuration files exist: phase registry, state schema, orchestrator rules.

A missing file means the system will fail at runtime when it tries to assemble a prompt for that phase.

### Check 2: Registry Integrity

The phase registry must be internally consistent.

**Verify:**
- Every phase has `display_name`, `purpose`, `allowed_targets`, and `conditions`.
- `default_phase` exists in the `phases` object.
- Every entry in `allowed_targets` references a phase that exists in the registry.
- Every entry in `allowed_targets` has a corresponding entry in `conditions`.
- Every phase is reachable from `default_phase` by following transition paths (no orphaned phases).
- At least one phase has an empty `allowed_targets` list or can become terminal via business rules (the conversation must be able to end).
- No phase lists itself in `allowed_targets`.
- No duplicate transitions (same source and target).
- `auto_advance` is explicitly set for every phase.

### Check 3: Schema Consistency

Field names must match across the state schema and the skill files. The state schema is the single source of truth for field definitions — the registry does not duplicate field lists.

**Verify:**
- Every phase in the registry has a corresponding phase entry in `state_schema.json`, and vice versa.
- For every phase: the fields described in `analyzer.md` match the fields defined in `state_schema.json` for that phase (same names, same types, same required/optional flags).
- For every phase: every field referenced in `speaker.md` (questioning strategy, acknowledgment guidance) has a corresponding entry in `state_schema.json`.
- Every field in the schema has `display_name` and `description`.

Field name mismatches are the most common configuration error. A typo in `analyzer.md` means the Analyzer will extract to a field name the Orchestrator doesn't recognize, and the extraction silently disappears.

### Check 4: Prompt Template Variables

The prompt templates must have all required variable placeholders.

**Analyzer template required variables:**
`{{active_phase_name}}`, `{{active_phase_state_json}}`, `{{active_phase_analyzer_md}}`, `{{phase_registry_summary}}`, `{{user_message}}`, `{{conversation_summary}}`, `{{recent_turns}}`

**Speaker template required variables:**
`{{active_phase_name}}`, `{{active_phase_speaker_md}}`, `{{phase_collected_data}}`, `{{phase_missing_required}}`, `{{phase_missing_optional}}`, `{{cross_phase_context}}`, `{{turn_type}}`, `{{turn_type_instructions}}`, `{{last_user_message}}`, `{{clarification_needed}}`, `{{conversation_summary}}`, `{{recent_turns}}`

**Summary template required variables:**
`{{conversation_summary}}`, `{{recent_turns}}`

A missing variable means that section will be absent from the assembled prompt, causing the LLM to operate without critical context.

### Check 5: Business Rule References

Orchestrator rules must reference valid phases and fields.

**Verify:**
- Every field-level rule references a phase that exists and a field that exists in that phase.
- Every cross-field rule references fields that exist in the same phase.
- Every transition rule references a transition that exists in the registry.

### Validation Summary

Run all five checks and produce a pass/fail report:

```
=== Pre-Deployment Validation ===

✓ File Completeness: 4 phases, all files present
✓ Registry Integrity: 4 phases, 5 transitions, all reachable
✓ Schema Consistency: all field names aligned
✓ Prompt Templates: all variables present (analyzer, speaker, summary)
✓ Business Rules: all references valid

Result: PASS (5/5 checks passed)
```

---

## Part 2: Functional Test Cases

These tests verify system behavior by running actual conversations through the pipeline. They require LLM calls.

### Category 1: Single-Turn Extraction Tests

Test that the Analyzer correctly extracts fields from individual messages. One test per extraction behavior.

**Example tests (interview prep domain):**

| Test | Input | Pre-State | Expected Extraction | Notes |
|------|-------|-----------|-------------------|-------|
| Single required field | "I'm interviewing at Google" | (empty) | `target_company: "Google"` | Basic extraction |
| Multiple fields | "Senior Software Engineer at Google, system design round" | (empty) | `target_company: "Google"`, `role_level: "senior"`, `role_title: "Senior Software Engineer"`, `interview_format: "system_design"` | Multi-field in one message |
| Ambiguous input | "I have an interview coming up" | (empty) | (empty) | Nothing specific to extract |
| Invalid enum | "I'm interviewing for a wizard-level position" | (empty) | `role_level` NOT extracted | Invalid value should be rejected |
| Correction | "Actually, it's Meta, not Google" | `target_company: "Google"` | `target_company: "Meta"` | Overwrite existing value |
| Array append | "Also distributed systems" | `technical_areas: ["React"]` | Append `"distributed systems"` | Post-merge: `["React", "distributed systems"]` |

**How to evaluate:** Allow reasonable variation in extracted values (e.g., "system design" vs "system_design" may both be acceptable depending on the analyzer.md normalization rules). Test structure and field presence, not exact strings.

### Category 2: Multi-Turn Conversation Tests

Test complete conversations across multiple turns and phase transitions.

**Happy path test:**

| Turn | User Message | Expected Behavior |
|------|-------------|-------------------|
| 1 | (opening) | Agent generates opening message asking about the interview |
| 2 | "I'm preparing for a Senior Software Engineer interview at Google" | Extracts company, level, role title. Speaker acknowledges, asks about format. |
| 3 | "It's a system design round next week" | Extracts format, timeline. Required complete. Speaker summarizes, confirms. |
| 4 | "Yes, that's right" | Confirmation detected (not re-extraction). Phase transition to next phase. Speaker transitions smoothly. |
| 5 | (answer to first question in new phase) | In new phase. Speaker follows up. |

**Correction flow test:**

| Turn | User Message | Expected Behavior |
|------|-------------|-------------------|
| 1 | (opening) | Opening message |
| 2 | "Google, Senior Frontend Engineer" | Extracts company, level, role title |
| 3 | "Wait, I meant Backend Engineer, not Frontend" | `role_title` overwritten to "Backend Engineer." Speaker acknowledges correction naturally. |

**Off-topic handling test:**

| Turn | User Message | Expected Behavior |
|------|-------------|-------------------|
| 1 | (opening) | Opening message |
| 2 | "What's the weather like today?" | Empty extraction. Speaker gently redirects. |
| 3 | "Sorry, I'm interviewing at Amazon" | Extracts `target_company: "Amazon"`. Speaker continues normally. |

### Category 3: Edge Case Tests

| Test | Input / Setup | Expected Behavior |
|------|--------------|-------------------|
| Empty message | "" | Analyzer handles gracefully. Speaker asks user to provide information. |
| Very long message (500+ words) | Long paragraph with embedded info | Analyzer extracts all relevant fields. No truncation of current-turn message. |
| Special characters | "I'm interviewing at O'Reilly & Associates" | Company name extracted correctly with special characters preserved. |
| Contradictory in same message | "I'm interviewing at Google, I mean Meta" | Analyzer extracts "Meta" (latest value). No conflict triggered. |
| First turn after transition | Just transitioned to new phase | Speaker generates new phase opening. Prior phase summary populated. |
| Max turns reached | `turn_count = max_turns - 1` | Orchestrator triggers termination. Speaker handles gracefully. |

### Category 4: Error Recovery Tests

| Test | Mock / Trigger | Expected Behavior |
|------|---------------|-------------------|
| Analyzer returns invalid JSON | Mock: "Here's my analysis: {invalid json" | Retry with stricter prompt. If retry fails, empty delta. Speaker continues. |
| Analyzer hallucinates a field | Mock: `{ "favourite_color": "blue", "target_company": "Google" }` | Unknown field stripped, valid field kept. |
| Speaker leaks field name | Mock: "Your target_company is Google" | Retry triggered. Clean output or fallback. |
| LLM timeout | Mock: 30+ second hang | Timeout triggered. Retry once. Fallback if retry also times out. |
| State persistence failure | Mock: state store returns error | State cached in memory. Response still delivered. Retry next turn. |

### Test Design Guidelines

**For extraction tests:**
- Test one specific extraction behavior per test case.
- Include the exact input message.
- Specify expected `extracted_fields` precisely.
- Test both positive (field IS extracted) and negative (field is NOT extracted from ambiguous input).
- Test corrections, array appends, and deduplication.
- Don't write tests that depend on exact Speaker wording — test structure and behavior, not prose.

**For multi-turn tests:**
- Test the complete happy path (every phase, start to finish).
- Test at least one correction flow and one off-topic scenario.
- Test phase transition boundaries explicitly, including the first Speaker message after a transition.
- Keep tests under 20 turns (longer tests are hard to maintain).
- Don't assert exact Speaker text — assert that it addresses the right topic and doesn't leak internals.

**For error recovery tests:**
- Mock LLM failures at each call point (Analyzer and Speaker independently).
- Test the full retry → fallback → escalation chain.
- Verify state integrity after recovery.
- Test that the user always receives a response, even when everything fails.

---

## Part 3: Runtime Debugging

When something goes wrong in production, use these diagnostic approaches.

### Debugging Data Sources

Every turn should produce artifacts that can be inspected after the fact:

| Artifact | Contains |
|----------|----------|
| State snapshot | Full state before and after the turn |
| Audit log | Orchestrator decisions: merges, transitions, rejections |
| History record | Raw user message and agent response |
| Error log | Any errors, retries, and fallbacks that occurred |

### Diagnostic Flowcharts

**"Why did the Analyzer miss that field?"**

1. Check the audit log: was the field in `extracted_fields`?
2. **If yes** → the Orchestrator rejected it. Check validation failures — hallucinated field? Type mismatch? Invalid enum?
3. **If no** → the Analyzer didn't extract it. Reconstruct the Analyzer prompt for that turn (load the state snapshot from before the turn, the analyzer.md, and the assembled history). Inspect: is the field definition clear enough? Does the user's message actually contain extractable information for that field?

**"Why did the Speaker ask for already-collected information?"**

1. Check the state snapshot from BEFORE Speaker assembly: was the field in `phase_collected_data`?
2. **If no** → the merge hadn't happened yet. The Speaker was assembled before the Orchestrator updated state (pipeline ordering bug).
3. **If yes** → the Speaker had the information and ignored it. Reconstruct the Speaker prompt. Check: is `{{phase_collected_data}}` populated correctly? Is the Speaker actually asking for that exact field, or a related but different one?

**"Why did it transition at the wrong time?"**

1. Check the audit log for the transition event: what was the trigger (completion, analyzer suggestion, timeout)?
2. **Unexpected transition** → check if `required_complete` was true. If it shouldn't have been, inspect completion status — was a field incorrectly marked as collected? Was a required field missing from the schema?
3. **Missing transition** → check if `required_complete` is true. If not, which fields are still missing? If yes, is there a completion transition in the registry? Are transition conditions blocking?

**"Why did the conversation get stuck?"**

1. Check consecutive empty extractions. If high (5+): are the user's messages off-topic, or is the analyzer.md too strict?
2. Check the Speaker's recent messages: is it asking the same question repeatedly? Is it asking for something the user can't or won't provide?
3. Check for unresolved conflicts blocking completion.
4. Check business rules: is a cross-field rule blocking? Was an optional-to-required field promotion triggered that the user doesn't know about?

### Debug Mode

For development and testing, the execution loop can run in debug mode that exposes internal state at every step. Debug output should include: the full assembled Analyzer prompt (with token count), the raw Analyzer response, the parsed Analyzer output, the pre- and post-Orchestrator state, the Orchestrator's decision log, the full assembled Speaker prompt (with token count), the raw Speaker response, and Speaker validation results.

### Conversation Replay

For diagnosing complex multi-turn issues, replay a conversation from recorded history by re-running each user message through the pipeline and comparing the replay output to the original. Replayed conversations won't produce identical text (even at temperature 0, model behavior varies slightly). The goal is to verify that the same inputs produce the same structural decisions — same fields extracted, same transitions triggered — not identical prose.

---

## Part 4: Continuous Monitoring

Tests that run in production to detect drift and degradation over time.

### Extraction Accuracy

Periodically sample completed conversations and evaluate:
- What percentage of turns produced extractions?
- How many hallucinated fields were stripped?
- How many turns had empty extractions that likely should have had them? (Requires human review of a sample.)
- How many `required_complete` flags were incorrect?

### Speaker Quality

Periodically sample Speaker output and check:
- Field name leaks (any internal names appearing in output)
- Phase name leaks
- Re-asked collected information
- Repetitive openings (e.g., "Great!" starting >30% of responses)
- Excessively long responses (>6 sentences)

### Conversation Completion Rate

Track whether conversations reach their intended outcome:
- Total conversations, completed, abandoned, errored
- Average turns to completion
- Average turns to abandonment (early abandonment suggests UX issues)
- Per-phase completion rates (identifies phases where users get stuck)

---

## Customization Points

### Validation Strictness

| Domain Type | Pre-Deployment | Functional Tests | Monitoring |
|---|---|---|---|
| Safety-critical (medical, legal, financial) | All 5 checks must pass with zero warnings | Full test suite including all edge cases and error recovery | Daily sampling, tight accuracy thresholds |
| Standard (intake forms, scheduling, coaching) | All 5 checks must pass | Happy path + correction + error recovery tests | Weekly sampling, moderate thresholds |
| Casual (exploration, brainstorming) | File completeness + registry integrity | Happy path + basic error recovery | Monthly sampling, loose thresholds |

### Monitoring Thresholds

Configure alert thresholds per domain:

| Metric | Strict (Medical) | Standard | Loose (Casual) |
|---|---|---|---|
| Extraction accuracy (turns with extraction / total) | >90% | >80% | >60% |
| Hallucinated field rate | <1% | <5% | <10% |
| Speaker leak rate | 0% | <2% | <5% |
| Conversation completion rate | >85% | >70% | >50% |
| Average turns to completion | <15 | <25 | No limit |

### Domain-Specific Test Cases

The test case examples above are from an interview prep domain. Every domain needs its own test cases covering:

1. **Domain-specific extraction patterns** — what does realistic user input look like in your domain? Medical symptoms? Financial details? Travel preferences?
2. **Domain-specific edge cases** — what unusual inputs does your domain encounter? Medical terminology? Legal jargon? Multilingual input?
3. **Domain-specific error scenarios** — what errors matter most in your domain? A medical bot must handle ambiguous symptom reports. A financial bot must handle currency and number formatting.

---

## Validation Checklist

### Pre-Deployment
- [ ] All phase skill files exist and are readable
- [ ] Registry integrity passes (all phases reachable, all have exits)
- [ ] Schema consistency passes (field names match across registry, schema, and skill files)
- [ ] Prompt templates have all required variables (analyzer, speaker, and summary templates)
- [ ] Business rules reference valid phases and fields

### Functional Tests
- [ ] Single-turn extraction tests pass for every phase
- [ ] Multi-turn happy path test passes end-to-end
- [ ] Correction flow test passes
- [ ] Off-topic handling test passes
- [ ] Phase transition tests pass (including first-turn-after-transition)
- [ ] Edge case tests pass (empty input, long input, special characters)
- [ ] Error recovery tests pass (invalid JSON, hallucinated fields, LLM failure)
- [ ] Conversation end test passes (both completion and abandonment)

### Runtime Monitoring
- [ ] Extraction accuracy sampling is active and within thresholds
- [ ] Speaker quality sampling is active and within thresholds
- [ ] Conversation completion rate is tracked and within thresholds
- [ ] Error rate monitoring is active with configured alerts
- [ ] Debug mode is available for investigation

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Testing AI output exactly | Tests fail because the Speaker said "Could you tell me about the role?" instead of "What role are you interviewing for?" Both are correct. | Test structure and behavior, not exact wording. Assert topic, absence of field names, acceptable length. |
| Not testing the seams | Analyzer extracts correctly in isolation. Speaker responds well in isolation. But in integration, the Speaker asks for already-collected info because state views were computed wrong. | Integration tests that run the full pipeline catch seam bugs. |
| No pre-deployment validation | Agent deployed with a typo in a field name in analyzer.md. Every extraction for that field fails silently. Discovered after 200 conversations. | Run all 5 pre-deployment checks before every deployment. |
| Testing only the happy path | Everything works in demos. In production, users go off-topic, send empty messages, correct themselves, and the system breaks. | Include corrections, off-topic, empty messages, contradictions, and error recovery in test cases. |
| No conversation replay capability | A user reports a bug but you can't reproduce it. You don't know what state the system was in or what prompts were assembled. | Store state snapshots, audit logs, and history. Build a replay tool. |
| Ignoring continuous monitoring | Extraction quality slowly degrades over months as the model gets updated. Nobody notices until the completion rate drops. | Run monitoring tests in production. Extraction sampling, Speaker quality sampling, and completion rate tracking catch gradual drift. |
