# Skill 2: Analyzer Prompt Template

## Purpose

This skill is the canonical reference for writing `prompts/analyzer_template.md` — the prompt template that drives the Analyzer component of a multi-phase information-extraction agent. The Analyzer's job is to interpret a user's message and propose a structured state delta. It does not generate user-facing text, does not mutate state, and does not make control decisions.

The analyzer template works alongside:

- Per-phase `analyzer.md` files — injected into the template at runtime to provide phase-specific extraction instructions
- `state_schema.json` — defines the fields the Analyzer extracts into
- `phase_registry.json` — provides the phase list for cross-phase detection

---

## Core Principles

1. **The Analyzer is a proposal engine.** It proposes extracted fields and phase suggestions. The State Updater decides what to accept. The prompt must reinforce this boundary — the Analyzer should never use language like "updating state" or "transitioning to."
2. **Structured output is non-negotiable.** The Analyzer must return valid JSON matching a defined schema. Every turn. No exceptions. No prose. No explanations outside the JSON. The prompt must enforce this relentlessly.
3. **Extract only what's explicit.** The single biggest source of errors is the Analyzer inferring information the user didn't state. The prompt must hammer this point with examples.
4. **One template, customized per domain.** The template provides the global structure — system role, extraction rules, output format, analysis tasks. Phase-specific behavior comes from injecting the phase's `analyzer.md` content into a placeholder. The global rules section may be customized for domains that need different extraction behavior, but the structure stays the same.
5. **Context is fuel, not noise.** Give the Analyzer exactly what it needs — current phase skill, current phase state, phase registry summary, recent history. More context isn't always better; irrelevant context degrades extraction quality.

---

## Template

### Complete Template

```
SYSTEM ROLE
You are an analysis agent responsible for interpreting a user's message
within a multi-phase information-collection workflow.

Your job is to analyze the user's message and propose a structured
STATE DELTA according to the instructions below.

You are a proposal engine. You do not update state. You do not make
transition decisions. You do not generate user-facing text. You only
analyze and propose.

---

GLOBAL RULES

Extraction rules:
- Extract ONLY information explicitly stated by the user.
- Do NOT infer, assume, or fabricate missing information.
- If information is partial, extract only what is present.
- If the user's message contains no extractable information for the
  current phase, return empty extracted_fields.
- If a value is ambiguous, extract the most likely interpretation and
  set confidence below 0.8.
- If the user corrects a previously provided value, extract the new
  value. The State Updater will handle the update policy.
- If the user provides multiple fields in a single message, extract
  all of them.

Cross-phase rules:
- If the message is unrelated to the current phase, evaluate whether
  it aligns with another phase using the phase registry below.
- If a different phase is more appropriate, identify the most likely
  phase with a confidence score.
- If cross-phase information is detected, extract fields relevant to
  the suggested phase, not the current phase.

Output rules:
- Output MUST be valid JSON matching the specified output format.
- Do NOT include any text outside the JSON object.
- Do NOT include explanations, commentary, or prose.
- Do NOT wrap the JSON in markdown code fences.

---

ACTIVE PHASE
Phase name: {{active_phase_name}}

Active phase data (already collected):
{{active_phase_state_json}}

---

ACTIVE PHASE ANALYZER SKILL
Below are the instructions that define:
- what information this phase is responsible for
- which fields are required vs optional
- how to interpret responses
- how to assess completion
- when to suggest a phase transition

{{active_phase_analyzer_md}}

---

PHASE REGISTRY (FOR DETECTION ONLY)
The following phases exist in this workflow.
Use this list ONLY to detect whether the user's message better aligns
with a different phase. Do not extract fields for phases other than
the current or suggested phase.

{{phase_registry_summary}}

---

RUNTIME CONTEXT
User's latest message:
{{user_message}}

Conversation summary:
{{conversation_summary}}

Recent turns:
{{recent_turns}}

---

ANALYSIS TASKS
Perform the following steps internally:

1. Determine whether the user's message provides information relevant
   to the current phase.
2. Extract any required or optional fields defined by the current
   phase skill. Follow the interpretation rules in the skill exactly.
3. Determine whether all required information for the current phase
   has been collected (considering both existing state and new
   extractions).
4. Evaluate whether the user's message better aligns with another
   phase from the registry.
5. If a different phase is more appropriate:
   a. Identify the target phase and confidence level.
   b. Re-evaluate the user's message using that phase's field
      definitions from the registry.
   c. Extract fields relevant to the suggested phase instead.

---

OUTPUT FORMAT
Return a single JSON object with the following shape:

{
  "extracted_fields": {},
  "required_complete": false,
  "phase_suggestion": null,
  "confidence": 0.0,
  "notes": ""
}

Field definitions:
- extracted_fields: Object containing field_name: value pairs for
  fields extracted from this turn's message. Include ONLY fields
  where a value was found. Do NOT echo existing state.
- required_complete: Boolean. True if ALL required fields for the
  current phase are now present (combining existing state + new
  extractions). False otherwise.
- phase_suggestion: String phase name if a different phase is more
  appropriate, or null if the current phase is correct.
- confidence: Float 0.0-1.0. Overall confidence in the extraction
  and any phase suggestion. Set below 0.8 for ambiguous extractions.
- notes: Brief internal note about extraction decisions, ambiguities,
  or edge cases encountered. Not shown to user.

---

IMPORTANT CONSTRAINTS
- Do NOT include user-facing language.
- Do NOT include control decisions.
- Do NOT include fields not described in the phase skill.
- Do NOT modify or restate existing state.
- Do NOT include explanations outside the JSON.
- Do NOT wrap output in markdown code fences.

Produce the JSON output now.
```

---

## Template Variables

Each `{{variable}}` is injected at runtime before the prompt is sent to the LLM.

| Variable | Source | Description |
|----------|--------|-------------|
| `{{active_phase_name}}` | Active phase from state | Name of the currently active phase. |
| `{{active_phase_state_json}}` | Phase data from state | JSON object of all fields for the current phase, including null values. The Analyzer needs to see what's collected AND what's missing. |
| `{{active_phase_analyzer_md}}` | File: `skills/{active_phase}/analyzer.md` | The full contents of the current phase's analyzer skill file. Injected verbatim — never summarized, truncated, or reformatted. |
| `{{phase_registry_summary}}` | Generated from phase registry | Condensed markdown summary of all phases (phase name, purpose, fields, transitions). Used for cross-phase detection only. |
| `{{user_message}}` | Current turn input | The raw user message for this turn. Unmodified. |
| `{{conversation_summary}}` | `state.conversationSummary` | Cumulative summary of conversation history up to the last summarization point. Empty string early in conversation. See Skill 7. |
| `{{recent_turns}}` | `state.messages` (from `lastSummarizedTurnIndex`) | Recent conversation turns since the last summary, formatted as a simple transcript with `[User]` and `[Assistant]` labels. Same format used by all components. See Skill 7. |

### Variable Formatting Notes

- **Include null fields in `{{active_phase_state_json}}`.** The Analyzer needs to see what's missing, not just what's present. Example: `{"target_company": "Google", "role_title": null, "role_level": "senior", "interview_format": null}`.
- **Never truncate `{{active_phase_analyzer_md}}`.** This is the Analyzer's core instruction set.
- **Never truncate `{{user_message}}`.** That's the input being analyzed.
- **Escape handling.** If the analyzer.md or user message contains characters that could break the prompt structure (e.g., `---` dividers that match the template's section dividers), escape or fence them appropriately.
- **Entity-bearing phases in `{{active_phase_state_json}}`.** For phases with entity structure, format the state to show the current entity's fields alongside phase-level fields. Include the entity index and total count for context. Example:

  ```json
  {
    "entity": "project (2 of 5)",
    "current_entity": {
      "project_name": "Data Pipeline",
      "project_role": null,
      "technologies": ["Python"]
    },
    "phase_level": {
      "overall_experience_theme": null
    },
    "prior_entities_summary": [
      "Project 1: API Gateway (Lead Engineer)"
    ]
  }
  ```

  The Analyzer needs to see: (a) which entity fields are collected and missing for the current entity, (b) phase-level field state, and (c) brief prior entity context to avoid re-extracting information from earlier entities. The `prior_entities_summary` is a compact list, not the full field set — just enough to prevent confusion.

---

## Expected Behavior by Scenario

These examples show what the Analyzer should produce for common situations. They test whether the template's global rules are working correctly.

### Empty or Irrelevant Messages

User sends "ok", "hmm", "I don't know", or something completely off-topic.

```json
{
  "extracted_fields": {},
  "required_complete": false,
  "phase_suggestion": null,
  "confidence": 0.9,
  "notes": "User message contained no extractable information for the current phase."
}
```

Confidence should be high — the Analyzer is confident there's nothing to extract, not uncertain about what to extract.

### Multi-Field Messages

User says: "I have a Google interview next week for a senior backend role, probably distributed systems stuff."

The Analyzer should extract all fields present in a single pass. The phase's analyzer.md should list fields in priority order so the most important ones are extracted first if the Analyzer misses any.

### Corrections

User says: "Actually, it's a mid-level role, not senior."

```json
{
  "extracted_fields": {
    "role_level": "mid"
  },
  "required_complete": false,
  "confidence": 0.95,
  "notes": "User corrected role_level from senior to mid."
}
```

The Analyzer extracts the new value. The State Updater applies the update policy.

### Cross-Phase Input

User is in "interview setup" but says: "Can you give me a system design question about distributed databases?"

```json
{
  "extracted_fields": {
    "topic_focus": "distributed databases"
  },
  "required_complete": false,
  "phase_suggestion": "question_practice",
  "confidence": 0.85,
  "notes": "User is requesting a practice question, which aligns with the question_practice phase."
}
```

The Analyzer detects the cross-phase intent using the phase registry, proposes a phase switch, and extracts fields relevant to the suggested phase. The State Updater decides whether to accept the transition.

### Entity Switch (Within an Entity-Bearing Phase)

User is in "experience_review" discussing project 1, and says: "I also worked on a real-time analytics platform."

```json
{
  "extracted_fields": {
    "project_name": "real-time analytics platform"
  },
  "required_complete": false,
  "phase_suggestion": null,
  "confidence": 0.85,
  "notes": "User appears to be introducing a new project entity. Extracted project_name for what would be the next entity. Phase suggestion is null because the user is staying in the same phase — entity rotation is handled by the State Updater."
}
```

The Analyzer does not signal a phase change for entity switches. It extracts fields normally. The State Updater detects that the extracted `project_name` is a new value while the current entity's `project_name` is already filled, and handles entity rotation.

**Important:** Entity-switch detection is NOT a cross-phase signal. The Analyzer should not set `phase_suggestion` for entity switches — that would trigger an unnecessary phase redirect loop. Entity rotation is a State Updater concern.

### Implicit Information

User asks: "What kind of questions should I expect for a system design interview?"

```json
{
  "extracted_fields": {
    "interview_format": "system_design"
  },
  "required_complete": false,
  "phase_suggestion": null,
  "confidence": 0.7,
  "notes": "User asked a question rather than providing info directly. Implicit mention of system design format extracted with moderate confidence."
}
```

The Analyzer extracts what it can and notes the uncertainty with lower confidence.

### Refusal

User says: "I'd rather not say which company" or "I don't know the format."

```json
{
  "extracted_fields": {},
  "required_complete": false,
  "phase_suggestion": null,
  "confidence": 0.9,
  "notes": "User declined to provide target_company. No extractable information."
}
```

The Analyzer does not extract anything and does not fabricate a value. It does not mark the field as "refused" — that's the State Updater's domain.

---

## Customization Points

The template provides sensible defaults for most domains. Here's where and when to customize it.

### Via Phase Skill Files (Preferred)

Most domain behavior should live in the phase's `analyzer.md` file, not in the template. This includes what fields to extract, how to interpret ambiguous values, completion criteria, and phase transition signals. Changing `analyzer.md` files requires no template changes.

### Via Global Rules (When Needed)

Modify the GLOBAL RULES section when the domain requires fundamentally different extraction behavior:

- **"Infer missing values from context"** — reverses the default "extract only explicit" rule. Use for domains where context-based inference is acceptable (e.g., inferring location from area code).
- **"All dates must be in ISO format"** — adds a global formatting constraint.
- **"Include a sentiment score"** — adds a field to the output format for domains like customer support.

### Via Output Format (Rare)

Modify the output format when the State Updater needs additional signals:

- Adding an `urgency` flag for triage systems
- Adding a `sentiment` score for customer support
- Supporting multi-entity extraction (e.g., info about multiple people in one message)
- Supporting entity-aware extraction for entity-bearing phases (handled by the Analyzer Prompt Creator's variable formatting, not by template changes)

### What Should NEVER Be Customized

- The separation between proposal and decision (Analyzer proposes, State Updater decides)
- The JSON-only output constraint
- The "extract only explicit" default (override per-phase in skill files if needed, not globally)
- The phase registry injection point

---

## Test Categories

Build test cases covering these categories for every phase:

| Category | Example | What to Assert |
|----------|---------|----------------|
| **Happy path** | User provides exactly one required field | Correct field extracted, others empty |
| **Multi-field** | User provides 3 fields in one message | All 3 extracted correctly |
| **Partial/ambiguous** | "some kind of backend role" | Extracted with lower confidence |
| **Correction** | "actually it's mid-level, not senior" | New value extracted, old value not echoed |
| **Empty/irrelevant** | "ok" or "how are you?" | Empty extracted_fields, high confidence |
| **Cross-phase** | User mentions info from another phase | Phase suggestion with confidence, fields for suggested phase |
| **Refusal** | "I'd rather not say" | Empty extracted_fields, no fabrication |
| **Contradiction** | Provides conflicting info | Extracted with notes about contradiction |
| **Completion** | Final required field provided | required_complete = true |
| **Already collected** | User repeats known info | Only new/changed values in extracted_fields |

When modifying the template or a phase's analyzer.md, run the full test suite for that phase. Template changes affect all phases, so check for regressions broadly. The "empty/irrelevant" and "cross-phase" categories are most sensitive to prompt changes.

---

## Worked Example

Here's what the variable sections look like for a specific turn of the mock interview agent. The system role, global rules, analysis tasks, output format, and constraints sections are the same as the template above — only the injected content changes.

**Scenario:** User is in interview_setup. Some fields already collected. User provides role title and interview format.

**Injected variables:**

```
ACTIVE PHASE
Phase name: interview_setup

Active phase data (already collected):
{
  "target_company": "Google",
  "role_title": null,
  "role_level": "senior",
  "interview_format": null,
  "interview_timeline": "next week",
  "technical_areas": ["distributed systems"],
  "preparation_level": null
}

---

ACTIVE PHASE ANALYZER SKILL
[full contents of skills/interview_setup/analyzer.md]

---

PHASE REGISTRY (FOR DETECTION ONLY)

### interview_setup — Interview Setup
Collects: target_company, role_title, role_level, interview_format
Optional: interview_timeline, technical_areas, preparation_level
Transitions to: question_practice (when all required complete)

### question_practice — Question Practice
Collects: questions_completed, user_responses
Optional: topic_focus
Transitions to: session_feedback (when practice complete)

### session_feedback — Session Feedback
Collects: feedback_acknowledged, wants_more_practice
Transitions to: question_practice (if looping)

---

RUNTIME CONTEXT
User's latest message:
I think it's called Senior Software Engineer, and it's going to be
a system design round.

Conversation summary:
(empty — conversation just started)

Recent turns:
[Assistant]: Hey! I'm here to help you prep for your interview...
[User]: I have a Google interview next week for a senior backend role...
[Assistant]: Nice, a senior backend role at Google — exciting! Could you
tell me the specific role title and what format the interview will be?
```

**Expected output:**

```json
{
  "extracted_fields": {
    "role_title": "Senior Software Engineer",
    "interview_format": "system_design"
  },
  "required_complete": true,
  "phase_suggestion": null,
  "confidence": 0.95,
  "notes": "User provided the specific role title and confirmed the interview format as system design. All four required fields are now present."
}
```

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Truncating the analyzer.md | Analyzer misses fields or misinterprets values | Never truncate — this is the Analyzer's core instruction set |
| Not including null fields in current phase state | Analyzer doesn't know what's missing | Always include all fields, even null ones |
| Injecting prose after "Produce the JSON output now" | Confuses the output boundary; may produce prose | The final line must be the output trigger with nothing after it |
| Including full analyzer.md for all phases | Token waste, confusion, cross-contamination | Include only the active phase's analyzer.md; registry summary for others |
| Not escaping user messages containing JSON-like content | Parser picks up user content instead of Analyzer output | Isolate user message in a clearly delimited section |
| Setting `phase_suggestion` for entity switches | Triggers phase redirect loop unnecessarily | Entity rotation is a State Updater concern; Analyzer extracts fields normally within the same phase |
| Not including prior entity summary in entity-phase state | Analyzer re-extracts information from earlier entities | Include compact `prior_entities_summary` in `{{active_phase_state_json}}` |
