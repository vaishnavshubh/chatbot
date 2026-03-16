# Skill 6: Orchestrator Rules Authoring

## Purpose

This skill is the canonical reference for writing `orchestrator_rules.md` — the plain-English configuration file that governs how the State Updater manages a specific agent's session flow, business logic, cross-phase context, operational limits, and execution behavior.

The domain customization process decides *which phases exist and how they connect*. This skill defines *how to write the rules that govern transitions, constraints, context passing, error handling, and runtime behavior for those phases*.

The `orchestrator_rules.md` file works alongside two other configuration artifacts:

- `state_schema.json` — defines every field's type, required/optional flag, update policy, and display name
- `phase_registry.json` — defines phase names, allowed transitions, conditions, and per-phase turn limits

The rules file is written in plain English markdown so it's readable by both humans and the State Updater at runtime — no special parser needed.

---

## Core Principles

1. **Rules are constraints, not procedures.** The rules file declares *what must be true* — not *how to implement it*. "Block transition to question_practice if company is null" is a rule. "Check if company field is null, then set the transition decision to stay" is an implementation detail that belongs in State Updater code.
2. **Every rule must be testable.** If you can't write a unit test for a rule (given this state, this rule fires/doesn't fire), the rule is too vague. "Be smart about transitions" is not a rule.
3. **Business rules override normal flow.** The State Updater evaluates phase completion and transition conditions first (from `phase_registry.json`), then applies business rules as overrides. Rules can block transitions, force transitions, or modify state on transition.
4. **Cross-phase context is explicit.** Don't assume the Speaker will figure out what context it needs from prior phases. List exactly which fields from which phases should be passed forward when entering each phase.
5. **Limits exist to prevent pathology.** Turn limits and timeouts aren't for normal conversations — they're safety nets for stuck sessions, infinite loops, and abandoned conversations.
6. **Execution behavior is domain-sensitive.** How aggressively the system retries on failure, what fallback messages it uses, what hooks run before and after the conversation — these vary by domain and belong in the rules file alongside transition logic and business constraints.

---

## Template

This is the canonical template. Every `orchestrator_rules.md` file must follow this structure.

```markdown
# Orchestrator Rules: [Agent Name]

## Transition Confidence

[Minimum confidence threshold for the State Updater to trust the
Analyzer's extractions and phase suggestions.]

## Default Phase Flow

[The default sequence of phases when no special conditions apply.
One line per transition.]

## Cross-Phase Context

[For each phase that needs context from earlier phases: which fields
to carry forward, from which source phases.]

## Business Rules

[Named rules that override normal transition logic. Each rule has
a descriptive name, the condition, and the action.]

## Entity Rotation Rules

[For entity-bearing phases: when to rotate to the next entity, what
context to carry between entities, and the exit condition.]

## Conversation Limits

[Turn limits and timeouts.]

## Hooks

[Extension points for domain-specific logic at defined pipeline
stages: pre-conversation, mid-pipeline, post-completion,
pre-resumption.]

## Error Tolerance

[Retry limits, consecutive error thresholds, and escalation
behavior. Tune per domain risk level.]

## Fallback Messages

[Domain-appropriate messages for when the Speaker fails after
all retries. One per turn type plus a termination message.]

## Resumption

[Whether abandoned conversations can be resumed, and for how long.]
```

---

## Section-by-Section Guidance

### Transition Confidence

Tells the State Updater how much to trust the Analyzer's output. The Analyzer returns a confidence score (0.0–1.0) with every extraction. Below the threshold, the State Updater still merges extracted fields but ignores the Analyzer's `phase_suggestion` and `required_complete` claims — it re-evaluates both independently by counting non-null required fields itself.

```
BAD:
## Transition Confidence
Use good judgment about when to transition.

GOOD:
## Transition Confidence
Do not transition between phases unless the Analyzer's confidence
is at least 0.7. Below that threshold, stay in the current phase
and ask for clarification.
```

The threshold is a single number. 0.7 is a good default. Raise it (0.8–0.9) for high-stakes domains where wrong transitions are costly. Lower it (0.5–0.6) for casual domains where conversational flow matters more than extraction precision.

### Default Phase Flow

Defines the happy-path sequence. When a phase completes and no business rules intervene, the State Updater advances to the target listed here.

```
BAD:
## Default Phase Flow
Phases go in order.

GOOD:
## Default Phase Flow
When a phase completes and no special conditions apply, advance
to the next phase in this default sequence:

- After interview_setup → go to question_practice
- After question_practice → go to session_feedback
- After session_feedback → go to question_practice (if looping)
```

Rules:
- One line per transition. Format: `After [source] → go to [target]`.
- Every phase must appear as a source at least once (unless it's terminal).
- Every target must be a real phase name from `phase_registry.json`.
- If a phase can loop (like session_feedback → question_practice), note the condition in parentheses.
- Terminal phases (conversation ends) don't need a "go to" line — just omit them or note explicitly: "session_feedback is terminal when wants_more_practice is false."

When `auto_advance` is true in the phase registry and the phase is complete, the State Updater advances to the default next phase listed here without waiting for the user to signal readiness.

### Cross-Phase Context

When the Speaker enters a new phase, it needs to know what was established in prior phases — otherwise it re-asks questions or loses conversational continuity. This section tells the State Updater exactly which fields to carry forward.

```
BAD:
## Cross-Phase Context
Pass relevant information between phases.

GOOD:
## Cross-Phase Context
When entering a phase, the Speaker needs context from earlier
phases to maintain conversational continuity and avoid re-asking.
Pass these fields forward:

When entering question_practice, include from interview_setup:
  target_company, role_title, role_level, interview_format,
  technical_areas

When entering session_feedback, include from interview_setup:
  target_company, interview_format
And include from question_practice:
  questions_completed
```

Rules:
- One block per target phase. Format: `When entering [target], include from [source]: [field list]`.
- Every field name must exist in the source phase's schema in `state_schema.json`.
- Only include fields the Speaker in the target phase actually needs. Don't dump everything — keep it focused.
- If a phase pulls from multiple source phases, list each source separately.
- The first phase never appears as a target (nothing precedes it).

When a transition fires, the State Updater looks up each listed field's value in state and formats it with the field's `display_name` from the schema (not raw field names) for the Speaker to use as conversational context.

**Common mistake: field names here don't match the schema.** If you write `company_name` but the schema says `company`, the State Updater can't find the field and the context is silently missing. Always copy field names from the schema, don't paraphrase them.

### Business Rules

These are the heart of the rules file. Business rules encode domain-specific constraints that the generic State Updater can't know about. They override normal transition logic.

Every rule must have:
1. **A descriptive name** (used in logs and tests)
2. **A condition** (when does this rule fire?)
3. **An action** (what happens when it fires?)

There are three types of business rules:

#### Transition blockers

Prevent a transition even when normal conditions are met.

```
### No practice without company
Block any transition to question_practice if
interview_setup.target_company has not been collected.
The user must provide at least the company name before
practice can begin.
```

#### Transition forcers

Force a transition that wouldn't happen under normal flow.

```
### Loop exit condition
When session_feedback.wants_more_practice is true,
transition back to question_practice for another round.
When it is false, the conversation ends — session_feedback
becomes the terminal phase.
```

#### State modifiers

Change a field value when a transition fires.

```
### No system design for junior candidates
If interview_setup.role_level is "junior" and
interview_setup.interview_format is "system_design",
override the format to "coding" when entering
question_practice. Junior candidates should not receive
system design questions.
```

Writing good business rules:

```
BAD:
### Handle edge cases
Make sure the conversation makes sense.

GOOD:
### No practice without company
Block any transition to question_practice if
interview_setup.target_company has not been collected.

BAD:
### Check seniority
If the user is junior, adjust things accordingly.

GOOD:
### No system design for junior candidates
If interview_setup.role_level is "junior" and
interview_setup.interview_format is "system_design",
override the format to "coding" when entering
question_practice.
```

Rules for writing rules:

- **Name the rule after what it prevents or enforces**, not after the mechanism. "No practice without company" is better than "Company null check."
- **Reference field names exactly as they appear in the schema.** Use `interview_setup.target_company`, not "the company field."
- **Be explicit about the action.** "Block transition" is clear. "Handle appropriately" is not.
- **One rule, one concern.** Don't combine unrelated constraints into a single rule.
- **State the reason.** "Junior candidates should not receive system design questions" — one sentence explaining *why* helps reviewers judge whether the rule is correct.

After computing the normal transition decision, the State Updater evaluates each business rule's condition against current state. Rules that fire can change the decision — a blocker prevents an advance, a forcer triggers one, a modifier changes a field value. Every fired rule is logged by name.

### Entity Rotation Rules

For phases that collect information about multiple instances of the same entity type (multiple projects, symptoms, products), this section defines when to rotate from one entity to the next, what context carries between entities, and when the entity loop ends.

Only include this section if the agent has entity-bearing phases (see Skill 4). If no phases use entity structure, write "No entity-bearing phases" explicitly.

```
BAD:
## Entity Rotation Rules
Rotate entities when appropriate.

GOOD:
## Entity Rotation Rules

### experience_review (entity: project)

Rotation trigger:
Rotate to next project when project_name, project_role, and
key_contribution are all collected for the current project, OR when
the user explicitly says they want to discuss another project (e.g.,
"Let me tell you about another one" or "I also worked on...").

Cross-entity context:
When rotating, the Speaker should briefly reference prior project
names so it can say "In addition to Project Alpha, tell me about
your next project." Do not carry full project details forward —
just the name.

Exit condition:
Exit the entity loop when the user indicates no more projects
("That's all my projects" or "No, that covers it"), OR when
max_entities (5) is reached. The Speaker should offer one
explicit prompt before exiting: "Do you have any other projects
you'd like to discuss?"

Minimum entities: 1
At least one project must be fully discussed before the phase
can complete.
```

Rules:
- One block per entity-bearing phase. Include the entity name from the schema's `entity_config`.
- **Rotation trigger** must be specific and testable. "When it feels right" is not a trigger. "When project_name and project_role are collected, or user initiates" is. Reference exact field names from the schema.
- **Cross-entity context** should be minimal. The Speaker only needs enough to reference prior entities naturally — usually just a name or identifier. Don't carry all fields.
- **Exit condition** is mandatory. Every entity loop must have an explicit exit. "User signals done" AND "max_entities reached" are both needed — the first for the normal case, the second as a safety net.
- **Minimum entities** defines a floor. The phase cannot complete with fewer entities than this, even if the user wants to move on.
- The Speaker should offer an explicit "any more?" prompt before exiting the entity loop, rather than silently advancing. This is a communication rule — the Speaker Prompt Creator uses it when assembling the `entity_transition` turn.

### Conversation Limits

Safety nets for pathological sessions. These are not normal termination conditions — they're guards against infinite loops, abandoned sessions, and runaway token costs.

```
## Conversation Limits

- Maximum 30 turns across the entire conversation.
- Conversation times out after 3600 seconds (1 hour)
  of inactivity.
```

Guidelines:
- **Global turn limit:** Set based on the realistic maximum for the domain. A 4-phase intake form might need 30 turns. A simple 2-phase flow might need 15. Err on the generous side — hitting the limit should be rare.
- **Timeout:** 3600 seconds (1 hour) is a reasonable default. Shorter for synchronous chat (15–30 minutes). Longer for async workflows.
- **Per-phase limits** are set in `phase_registry.json`, not here. This section is for global limits only.

When the global turn limit is exceeded, the State Updater ends the conversation regardless of phase status, and the Speaker generates a wrap-up message using the termination fallback message.

### Hooks

Defines extension points where domain-specific logic plugs into the execution pipeline. The core pipeline (Analyzer Prompt Creator → Analyzer → State Updater → Speaker Prompt Creator → Speaker) is invariant. Hooks run *around* the pipeline at four defined points. Each is optional — write "none" explicitly if the domain doesn't need it.

```
BAD:
## Hooks
Handle setup and teardown.

GOOD:
## Hooks

### Pre-Conversation
- Verify patient identity via API
- Collect data processing consent
- Load patient history from EHR

### Mid-Pipeline
- none

### Post-Completion
- Submit collected data to EHR
- Schedule follow-up appointment
- Notify care team

### Pre-Resumption
- Re-verify patient identity
- Check whether collected symptoms have changed
```

The four hook points:

- **Pre-Conversation** — Runs once before the first turn. Use for authentication, consent, loading external data. If a pre-conversation hook fails, the conversation should not start.
- **Mid-Pipeline** — Runs after the State Updater updates state but before the Speaker Prompt Creator assembles the speaker prompt. Use for external API calls (fetching availability, portfolio values), safety filters, or data enrichment. Must be fast and resilient — if a hook fails, log and proceed, don't block the Speaker.
- **Post-Completion** — Runs after the final turn's response is sent. Use for submitting data to external systems, generating reports, sending notifications. Does not affect the conversation — the user has already received their closing message.
- **Pre-Resumption** — Runs when resuming an abandoned conversation. Use for re-verifying identity, refreshing stale data, checking availability.

Rules:
- Hooks must be specific and actionable. "Do setup" is not a hook. "Verify patient identity via API" is.
- Describe *what* each hook does, not *how* it's implemented. Implementation belongs in the codebase.
- Not every agent needs hooks. Don't add them "just in case" — each hook is a potential failure point.

### Error Tolerance

Configures how aggressively the system escalates on repeated failures. See Skill 8 (Error Recovery and Graceful Degradation) for the full error catalog and recovery strategies.

```
BAD:
## Error Tolerance
Handle errors well.

GOOD:
## Error Tolerance

- Max Analyzer retries: 2
- Max Speaker retries: 1
- Consecutive error threshold: 2
- Escalation action: terminate
  Medical triage must not continue on repeated failures.
```

The four parameters: Max Analyzer retries (default 2), Max Speaker retries (default 1), Consecutive error threshold (default 3), and Escalation action — `alert` (notify monitoring, continue), `terminate` (end gracefully), or `switch_model` (fall back to simpler model).

Tune by domain risk:

| Domain Type | Threshold | Escalation |
|---|---|---|
| Safety-critical (medical, legal, financial) | 1–2 | terminate |
| Standard (intake forms, coaching, scheduling) | 3 | alert |
| High-tolerance (casual chat, exploration) | 5+ | switch_model |

### Fallback Messages

When the Speaker fails after all retries, the system uses these messages instead. One per turn type plus a termination message.

```
BAD:
## Fallback Messages
Be helpful when things go wrong.

GOOD:
## Fallback Messages

- first_turn: "Hello, I'm here to help gather some
  information before your appointment. What brings
  you in today?"
- standard: "Thank you. Could you tell me a bit more
  about what you're experiencing?"
- phase_transition: "Thank you for that information.
  Now I'd like to ask about your medical history."
- clarification: "I want to make sure I have this right —
  could you help me understand that last detail?"
- entity_transition: "Thanks for walking me through that.
  Do you have another one you'd like to discuss?"
- termination: "I'm sorry, but I'm having trouble
  processing your information right now. Please contact
  the front desk at [number] for assistance."
```

Rules:
- Match the agent's tone. A user shouldn't be able to tell the system switched to a fallback.
- The termination message must include what to do next — not just "start over." For safety-critical domains, include an alternative contact.

Generic defaults (used if no fallback messages are configured):
- first_turn: "Hi there! Let's get started. Could you tell me a bit about what you're looking for?"
- standard: "Thanks for that! Could you tell me a bit more?"
- phase_transition: "Great, let's move on to the next step."
- clarification: "I want to make sure I understand correctly — could you clarify that last point?"
- entity_transition: "Thanks for that! Do you have another one you'd like to share?"
- termination: "I apologize, but I've encountered an issue I can't recover from. Please try starting a new conversation."

### Resumption

Configures whether abandoned conversations can be resumed and for how long persisted state is kept.

```
BAD:
## Resumption
Support resumption.

GOOD:
## Resumption

- Enable resumption: yes
- Resumption TTL: 3600 seconds (1 hour)
  Medical intake data becomes stale quickly.
```

Rules:
- Enable for any domain where users might disconnect and return (most domains).
- Set TTL based on data staleness. Medical data: hours. Shopping preferences: days. Interview prep: weeks.
- If pre-resumption hooks are configured, they run on resume — document what they verify.
- Disabling resumption is acceptable for very short conversations where restarting is trivial.

---

## Craft Guidance

### Business rules should be derivable from requirements

Every business rule should trace back to a specific requirement, constraint, or edge case in the domain requirements document. If you can't point to the reason a rule exists, it probably shouldn't be there.

```
Requirement: "System design questions only for mid-level and above"
→ Rule: "No system design for junior candidates"

Requirement: "Must know company and format before starting practice"
→ Rule: "No practice without company"

Requirement: "Maximum 20 turns per session"
→ Conversation Limits: "Maximum 20 turns"
```

If the requirements are silent on something, don't invent rules "just in case." Rules are constraints, and unnecessary constraints make the conversation rigid.

### Cross-phase context should be minimal

Pass only what the Speaker needs to maintain conversational continuity. The more context you pass, the more tokens you spend and the more likely the Speaker is to over-reference prior information.

```
BAD — dump everything:
When entering session_feedback, include from interview_setup:
  target_company, role_title, role_level, interview_format,
  interview_timeline, preparation_level

GOOD — only what the Speaker needs to frame feedback:
When entering session_feedback, include from interview_setup:
  target_company, interview_format
And include from question_practice:
  questions_completed
```

Ask: "What would the Speaker sound wrong without?" That's what to include.

### Loop rules need an exit condition

If any business rule creates a loop (phase A → phase B → phase A), there must be a corresponding rule that breaks the loop. Otherwise the conversation runs forever.

```
BAD — loop with no exit:
### Continue practice
When session_feedback is complete, transition back
to question_practice.

GOOD — loop with explicit exit:
### Loop exit condition
When session_feedback.wants_more_practice is true,
transition back to question_practice for another round.
When it is false, the conversation ends — session_feedback
becomes the terminal phase.
```

The global turn limit provides a backstop, but it shouldn't be the primary exit mechanism for a loop.

### Confidence threshold matches domain risk

The default 0.7 works for most domains. But consider:

- **High-stakes domains** (medical intake, legal questionnaire): Use 0.8–0.9. Wrong transitions or misextracted data can have real consequences. Better to ask for clarification than to proceed on a guess.
- **Low-stakes domains** (preference surveys, casual onboarding): Use 0.5–0.6. Conversational flow matters more than extraction precision. Asking "could you clarify?" on every ambiguous message gets annoying fast.
- **Mixed domains** (interview prep — setup is high-stakes, practice is low-stakes): Use the higher threshold. The confidence check applies globally, and it's better to be cautious during setup than to be too loose during practice.

### Error tolerance matches domain risk

The error tolerance section and the confidence threshold should align. A safety-critical domain should have both a high confidence threshold (0.8–0.9) and a low error tolerance (threshold 1–2, escalation terminate). A casual domain should have both a low confidence threshold (0.5–0.6) and a high error tolerance (threshold 5+, escalation switch_model). Mismatched risk profiles create inconsistent behavior.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Field names in cross-phase context don't match schema | State Updater can't find the field, context silently missing | Copy field names from state_schema.json exactly |
| Business rule references a phase not in the registry | Rule never fires or causes an error | Verify every phase name against phase_registry.json |
| Loop rule with no exit condition | Conversation loops indefinitely until turn limit | Every loop rule must have a paired exit condition |
| Vague business rules ("handle edge cases appropriately") | State Updater can't interpret the rule; it gets ignored | Make every rule testable: specific condition → specific action |
| Rules file restates what's already in phase_registry.json | Conflicting authority on transition logic | phase_registry.json defines *allowed* transitions; rules file defines *constraints on* those transitions. Don't duplicate. |
| Cross-phase context includes every field from prior phases | Token waste, Speaker over-references old info | Include only fields the Speaker needs for continuity |
| No global turn limit | Stuck conversations run forever | Always set a global turn limit, even if generous |
| Confidence threshold too low for the domain | State Updater accepts bad extractions and makes wrong transitions | Match the threshold to the domain's risk tolerance |
| Business rule combines multiple unrelated constraints | Hard to test, hard to debug when one condition is wrong | One rule, one concern — split compound rules |
| No error tolerance section | System uses defaults that may not match domain risk | Always configure error tolerance explicitly, especially for safety-critical domains |
| Generic fallback messages in a domain-specific agent | User gets a jarring tone shift when fallbacks fire | Write fallback messages that match the agent's established tone |
| Hooks without timeout or failure handling | Slow or broken hook blocks the entire conversation | Document that hooks must be fast and resilient; mid-pipeline hooks should not block the Speaker |
| Error threshold too high for safety-critical domain | System stumbles through repeated failures when it should stop | Match error tolerance to domain risk — safety-critical domains use threshold 1–2 with terminate escalation |
| Termination message with no next-step guidance | User is stranded when the system terminates | Termination message should always tell the user what to do next |
| Resumption enabled with no TTL | Stale data persists indefinitely | Set TTL based on how quickly collected data becomes stale |
| Entity rotation rule with no exit condition | Entity loop runs indefinitely until phase turn limit | Every entity rotation rule must have paired exit condition |
| Cross-entity context carries all fields | Token waste, Speaker over-references prior entities | Carry only identifiers (names, titles) — enough to reference, not repeat |
| Entity rotation trigger references fields not in per_entity_fields | Trigger never fires — field is in wrong scope | Rotation triggers should only reference per_entity required fields |

---

## Consistency Checklist

Run this before finalizing `orchestrator_rules.md`.

### Against state_schema.json:
- [ ] Every field name in the Cross-Phase Context section exists in the schema
- [ ] Every field name in Business Rules exists in the schema
- [ ] Field references use the format `phase_name.field_name` for clarity

### Against phase_registry.json:
- [ ] Every phase name in Default Phase Flow exists in the registry
- [ ] Every transition target in Default Phase Flow is in the source phase's `allowed_targets`
- [ ] Every phase referenced in Business Rules exists in the registry
- [ ] Every phase referenced in Cross-Phase Context (both source and target) exists in the registry

### Internal consistency:
- [ ] Every loop has an exit condition
- [ ] No business rule contradicts another business rule
- [ ] Transition confidence threshold is explicitly stated (not left to defaults)
- [ ] Global turn limit is set
- [ ] Error tolerance thresholds are explicitly set
- [ ] Fallback messages are present for all five turn types (first_turn, standard, phase_transition, clarification, entity_transition) plus a termination message
- [ ] Hooks are either specified or explicitly marked "none" at each hook point
- [ ] Resumption is configured with a TTL

### Risk alignment:
- [ ] Confidence threshold matches domain risk level
- [ ] Error tolerance matches domain risk level
- [ ] Confidence and error tolerance are consistent with each other (both conservative or both lenient, not mismatched)
- [ ] Termination message includes next-step guidance for safety-critical domains
- [ ] Escalation action is appropriate for the domain (terminate for safety-critical, alert or switch_model for standard/casual)

### Against phase skill files:
- [ ] Fields passed in cross-phase context are actually used by the target phase's speaker.md
- [ ] Business rules don't create transitions that skip phases with required fields — unless those fields are already collected or the skip is intentional
- [ ] Fallback messages match the tone established in the phase speaker.md files
- [ ] Entity-bearing phases' speaker.md files include entity transition guidance
- [ ] Entity-bearing phases' analyzer.md files include entity-switch detection examples

### Entity rules:
- [ ] Every entity-bearing phase has a rotation trigger, cross-entity context spec, and exit condition
- [ ] Entity rotation triggers reference valid per_entity field names from the schema
- [ ] Entity exit conditions include both user-initiated and max_entities safety net
- [ ] Minimum entities is set for each entity-bearing phase
- [ ] Entity rotation rules section exists (or explicitly states "No entity-bearing phases")
