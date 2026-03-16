# Skill 5: Phase Registry

## Purpose

This skill is the canonical reference for creating and maintaining the **phase registry** (`phase_registry.json`) — the central index of all phases in a multi-phase information-extraction agent. The registry serves three critical functions:

1. **Cross-phase detection**: The Analyzer uses the registry to recognize when a user's message belongs to a different phase than the one currently active.
2. **Transition routing**: The Orchestrator uses the registry to validate and execute phase transitions.
3. **System integrity**: The registry is the single source of truth for what phases exist, how they connect, and what constraints govern movement between them.

The registry is a configuration file, not code. It is consumed by both the Analyzer prompt (as `{{phase_registry_summary}}`) and the Orchestrator (for transition validation).

---

## Core Principles

1. **The registry is the map, not the territory.** It describes phases and connections. The phase skill files (`analyzer.md`, `speaker.md`) contain the actual behavior. The state schema owns field definitions. The registry declares structure and transitions — nothing more.
2. **Every phase must be registered.** If a phase has skill files but isn't in the registry, the Analyzer can't detect it and the Orchestrator can't transition to it. Unregistered phases don't exist to the system.
3. **Transitions must be explicit.** If a transition isn't declared in the registry, it's not allowed. The Orchestrator rejects undeclared transitions regardless of what the Analyzer suggests.
4. **The registry must stay in sync.** When you add, remove, or rename a phase, the registry, skill files, state schema, and orchestrator rules must all be updated together.
5. **Don't duplicate what the schema owns.** The registry does not list fields. Field names, types, required/optional status, and update policies live in `state_schema.json`. The registry references phases; the schema references fields within those phases. This avoids the sync bugs that come from maintaining the same field list in two places.

---

## Registry Format

### JSON Format (Recommended)

```json
{
  "version": "1.0",
  "default_phase": "interview_setup",
  "phases": {
    "interview_setup": {
      "display_name": "Interview Setup",
      "purpose": "Collect details about the user's upcoming interview: company, role, level, and format.",
      "allowed_targets": ["question_practice"],
      "conditions": {
        "question_practice": "all_required_complete"
      },
      "max_turns": null,
      "auto_advance": true,
      "order": 1
    },
    "question_practice": {
      "display_name": "Question Practice",
      "purpose": "Conduct mock interview questions tailored to the user's target role, company, and format.",
      "allowed_targets": ["session_feedback", "interview_setup"],
      "conditions": {
        "session_feedback": "user_requests_advance",
        "interview_setup": "user_requests_backtrack"
      },
      "max_turns": 15,
      "auto_advance": false,
      "order": 2
    },
    "session_feedback": {
      "display_name": "Session Feedback",
      "purpose": "Collect the user's confidence level and determine whether they want more practice or are done.",
      "allowed_targets": ["question_practice"],
      "conditions": {
        "question_practice": "user_requests_advance"
      },
      "max_turns": 5,
      "auto_advance": false,
      "order": 3
    }
  }
}
```

The structure is intentionally flat. There are no nested `transitions` or `constraints` objects — `allowed_targets`, `conditions`, `max_turns`, and `auto_advance` sit directly on the phase entry. This makes the registry easy to read, easy to generate, and easy to consume programmatically.

### Markdown Format (For Prompt Injection)

When the registry is injected into the Analyzer prompt as `{{phase_registry_summary}}`, generate a condensed markdown format optimized for AI comprehension. The summary generator pulls field information from the state schema at assembly time, so the registry itself never duplicates field lists.

**Example output:**

```markdown
## Phase Registry

### interview_setup — Interview Setup
Purpose: Collect details about the user's upcoming interview: company, role, level, and format.
Collects: target_company, role_title, role_level, interview_format
Optional: interview_timeline, technical_areas, preparation_level
Transitions to: question_practice (when all required complete)

### question_practice — Question Practice
Purpose: Conduct mock interview questions tailored to the user's target role, company, and format.
Collects: questions_completed
Transitions to: session_feedback (when user is ready), interview_setup (if user wants to go back)

### session_feedback — Session Feedback
Purpose: Collect the user's confidence level and determine whether they want more practice or are done.
Collects: feedback_acknowledged, wants_more_practice
Transitions to: question_practice (when user is ready)
```

This gives the Analyzer enough context to detect cross-phase input without the overhead of the full JSON structure. The field lists come from the schema at generation time, so they're always in sync.

---

## Field Reference

### Phase Entry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `display_name` | string | Yes | Human-readable phase name. Used in the Analyzer's registry summary and in logging. |
| `purpose` | string | Yes | One-sentence description of what this phase does. Used by the Analyzer for cross-phase detection. Must be specific enough to distinguish from other phases. |
| `allowed_targets` | string[] | Yes | Phase names this phase can transition to. Empty array means terminal phase. |
| `conditions` | object | Yes | Per-target transition conditions (see Transition Conditions below). Every entry in `allowed_targets` must have a corresponding condition. |
| `max_turns` | integer \| null | No | Maximum turns allowed in this phase before forced transition or escalation. Null means no limit. Default: null. |
| `auto_advance` | boolean | No | When true, the Orchestrator automatically transitions as soon as all required fields are complete, without waiting for the user to signal readiness. When false, the Orchestrator waits for an explicit trigger. Default: false. |
| `order` | integer | No | Sequence order. Does not enforce execution order — transitions do that. Useful for linear workflows and for the Orchestrator to determine "next logical phase." |

**Turn counting convention:** A "turn" counts each complete exchange (agent response, whether or not there was user input). The opening message counts as turn 1. This convention applies to both per-phase `max_turns` and the global turn limit in `orchestrator_rules.md`.

### What's NOT in the Registry

| Concern | Where It Lives | Why |
|---------|---------------|-----|
| Field names and types | `state_schema.json` | Single source of truth for field definitions. Duplicating in registry creates sync bugs. |
| Required vs. optional fields | `state_schema.json` | The `required` flag on each field in the schema is authoritative. |
| Update policies | `state_schema.json` | Per-field concern, not a phase-level concern. |
| Business rules | `orchestrator_rules.md` | Business rules are domain logic that the Orchestrator interprets. |
| Cross-phase display config | `orchestrator_rules.md` | Which fields from phase A to surface in phase B is an orchestration concern. |
| Extraction rules | `analyzer.md` per phase | Phase skill files own extraction behavior. |
| Conversational tone | `speaker.md` per phase | Phase skill files own communication behavior. |

### Transition Conditions

Each entry in `conditions` maps a target phase name to a condition string. The Orchestrator evaluates these conditions to decide whether to allow a transition.

| Condition | Meaning |
|-----------|---------|
| `all_required_complete` | All required fields for the current phase are present and valid. The most common condition. |
| `user_requests_advance` | User explicitly asks to move forward. Orchestrator may still block if required fields are missing and the phase isn't skippable. |
| `user_requests_backtrack` | User explicitly asks to go back to a previous phase. |
| `max_turns_exceeded` | The phase has hit its turn limit. Orchestrator triggers forced transition. |
| `always` | Transition is always allowed (no precondition). Use sparingly — typically for error recovery or escape hatches. |
| `{custom_condition}` | Domain-specific condition evaluated by the Orchestrator. Document these in `orchestrator_rules.md`. |

Conditions can be combined with `+` for AND logic:

```json
"conditions": {
  "session_feedback": "all_required_complete + user_requests_advance"
}
```

This means: transition to session_feedback only when all required fields are complete AND the user explicitly asks to proceed.

### auto_advance Behavior

When `auto_advance` is true for a phase:

1. The Orchestrator checks completion after every field update.
2. As soon as `required_complete` flips to true, the Orchestrator evaluates the transition condition for the default next target.
3. If the condition is `all_required_complete` (the most common case for auto-advance phases), the transition fires immediately without waiting for a user signal.

When `auto_advance` is false:

1. Completion is tracked but does not trigger transitions.
2. The Orchestrator waits for the Analyzer to detect a `user_requests_advance` signal or for a `max_turns_exceeded` trigger.

**When to use auto_advance:**
- Pure information collection phases where there's nothing to "do" after collecting — the user doesn't need to confirm.
- Phases where the transition should feel seamless (e.g., "setup" → "practice").

**When NOT to use auto_advance:**
- Interactive phases (practice, quizzes, exercises) where the user controls pacing.
- Phases where the user should review what was collected before moving on.
- Phases with conditional branches where the user should choose the path.

---

## Transition Topologies

Different domains call for different phase structures. The registry supports all of the following topologies. When designing a new agent, identify which topology matches the domain's natural conversation flow — don't force a linear structure onto a branching workflow or vice versa. Most real agents use one primary topology, sometimes with elements of a second (e.g., a linear flow with one iterative loop phase).

### Linear

Phases execute in fixed order. Each phase transitions to exactly one next phase.

```
phase_a → phase_b → phase_c → phase_d
```

Registry pattern: each phase has one entry in `allowed_targets` with `all_required_complete` as the condition. Set `auto_advance: true` for a smooth flow.

**When to use:** Simple intake forms, step-by-step wizards, sequential processes where later phases depend on earlier ones (insurance claim intake, medical history questionnaire, tax preparation).

**Key decisions:**
- Transition conditions are always `all_required_complete`
- `auto_advance: true` for all phases
- Simple, predictable, easy to test

### Linear with Backtracking

Like linear, but users can go back to previous phases to correct information.

```
phase_a ⇄ phase_b ⇄ phase_c → phase_d
```

Registry pattern: each phase has its forward target plus a `user_requests_backtrack` transition to the previous phase. The forward condition is typically `all_required_complete`; the backward condition is `user_requests_backtrack`.

**When to use:** Processes where users commonly need to revise earlier answers, like configuring a complex product where later choices affect earlier ones.

**Key decisions:**
- When backtracking, the Orchestrator preserves state from the target phase — the user doesn't have to re-answer everything
- The Speaker in the backtracked-to phase should acknowledge the return and ask what the user wants to change, not restart the phase from scratch
- The final phase (phase_d above) typically has no backtrack transition — once you reach wrap-up, you're done

### Branching

A phase can lead to different next phases based on collected data or user choice.

```
                  ┌──────────┐
             ┌───▶│ Branch 1 │───┐
┌─────────┐  │    └──────────┘   │  ┌─────────┐
│ Triage  │──┤                   ├─▶│ Wrap-up │
└─────────┘  │    ┌──────────┐   │  └─────────┘
             └───▶│ Branch 2 │───┘
                  └──────────┘
```

Registry pattern: the branching phase lists all possible targets in `allowed_targets`, each with its own condition. The Orchestrator decides which branch to take based on collected data (branching logic lives in `orchestrator_rules.md`, not in the registry). Set `auto_advance: false` — branching phases need explicit routing.

**When to use:** Workflows that fork based on user type, preference, or earlier answers (support ticket routing: technical vs. billing; loan application: personal vs. business; onboarding: individual vs. enterprise).

**Key decisions:**
- The triage phase determines the branch — its fields must include whatever data the business rules evaluate
- Business rules in `orchestrator_rules.md` encode the branching logic
- Branch phases may have different fields in the state schema
- Both branches converge to a common wrap-up phase
- The wrap-up phase should gracefully handle data from either branch

### Iterative Loop

A phase loops back to an earlier phase for repeated interaction.

```
┌─────────┐    ┌──────────┐    ┌──────────┐
│  Setup  │───▶│ Activity │◀──▶│ Feedback │
└─────────┘    └──────────┘    └──────────┘
                                     │
                                     ▼ (when done)
                               ┌──────────┐
                               │  Summary │
                               └──────────┘
```

Registry pattern: the feedback phase has both a loop-back target (to the activity phase) and a forward target (to the summary phase). The loop exit is controlled by business rules in `orchestrator_rules.md`. Set `auto_advance: false` on the feedback phase — the user decides whether to continue.

**When to use:** Interview practice (multiple questions), tutoring (multiple exercises), brainstorming (multiple rounds).

**Key decisions:**
- The feedback phase has a field (e.g., `wants_more`) that controls the loop
- State tracks iteration count across loops
- The activity phase resets certain fields each iteration (e.g., the current question) while preserving cumulative fields (e.g., total questions completed)
- The summary phase is terminal — only reachable when the loop ends
- Business rules must encode the loop exit condition explicitly — every loop needs an exit
- The global turn limit in `orchestrator_rules.md` provides a backstop, but it shouldn't be the primary exit mechanism

### Progressive Disclosure

Some phases are conditionally relevant based on earlier answers. An optional phase can be entered or skipped depending on collected data.

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│  Basic  │───▶│ Standard │───▶│ Advanced │───▶│  Done   │
└─────────┘    └────┬─────┘    └──────────┘    └─────────┘
                    │                                ▲
                    └────────────────────────────────┘
                         (skip if not needed)
```

Registry pattern: the phase before the optional phase has two entries in `allowed_targets` — one to the optional phase, one to the phase after it. Each target has its own condition. Business rules in `orchestrator_rules.md` determine whether the optional phase is entered or skipped based on state from earlier phases. Set `auto_advance: false` on the branching phase so the Orchestrator can evaluate the skip condition before advancing.

**When to use:** Workflows where some information is only relevant for certain users. Medical intake (detailed history only if symptoms warrant it), onboarding (advanced settings only if requested), loan applications (additional documentation only for certain loan types).

**Key decisions:**
- The "skip" condition must be a testable business rule based on collected state — not a vague judgment call
- The optional phase must handle being skipped — downstream phases and the summary shouldn't reference data that may not exist
- If multiple phases can be skipped, each skip condition is independent — don't create a cascade where skipping one phase forces skipping another unless the domain truly requires it

### Negotiation / Convergence

Two topics need to be balanced against each other, with the conversation moving back and forth until both are stable.

```
┌─────────┐    ┌──────────┐    ┌──────────┐
│  Setup  │───▶│ Topic A  │◀──▶│ Topic B  │
└─────────┘    └──────────┘    └────┬─────┘
                                    │
                                    ▼ (converged)
                               ┌──────────┐
                               │ Finalize │
                               └──────────┘
```

Registry pattern: bidirectional transitions between the two topic phases, each with `user_requests_advance` as the condition. A forward transition from either topic phase to the finalize phase requires a custom condition (e.g., `both_topics_stable`) defined in `orchestrator_rules.md`. Set `auto_advance: false` on both topic phases — the user controls when to switch between topics.

**When to use:** Conversations where changing one variable affects another. Job offer negotiation (salary ↔ benefits), project scoping (features ↔ timeline), travel planning (destinations ↔ budget).

**Key decisions:**
- The convergence condition checks that both topics have stable values — define this as a business rule
- May need a "changed" flag per topic that resets when the user revisits it, so the Orchestrator can detect when both topics have settled
- Set `max_turns` on both topic phases to prevent infinite ping-pong
- The finalize phase should only be reachable when the convergence condition is met
- This is the most complex topology — consider whether the domain truly requires back-and-forth balancing or whether a simpler branching or linear flow would suffice

### Free-Form (Hub and Spoke)

Any phase can transition to any other phase. There's a central "hub" or the user navigates freely.

```
phase_a ⇄ phase_b ⇄ phase_c
   ⇅         ⇅         ⇅
phase_d ⇄ phase_e ⇄ phase_f
```

Registry pattern: every phase lists all other phases in `allowed_targets` with `always` as the condition.

**When to use:** Exploratory conversations where information can come in any order, like a general consultation or discovery call. Use with caution — more freedom means more complexity in the Orchestrator. Always set `auto_advance: false`.

**Key decisions:**
- Cross-phase detection in the Analyzer becomes critical — the `purpose` field on each phase must be specific enough to distinguish them
- The Orchestrator needs clear business rules to prevent chaotic bouncing between phases
- Consider whether a hub-and-spoke model (one central phase that branches to topic phases and back) is more manageable than fully free-form
- Completion logic is more complex — define what "done" means across all phases in the business rules

### Terminal Phases

A terminal phase has no outgoing transitions. It's the end of the workflow.

```json
"session_feedback": {
  "display_name": "Session Feedback",
  "purpose": "Wrap up the session.",
  "allowed_targets": [],
  "conditions": {},
  "auto_advance": false,
  "order": 4
}
```

The Orchestrator treats arrival at a terminal phase (with all required fields complete) as conversation completion.

A phase can be **conditionally terminal** — it has `allowed_targets` but business rules may prevent all of them from firing, making it effectively terminal. This is a valid pattern for iterative workflows where the user can choose to stop (e.g., the feedback phase in an iterative loop becomes terminal when `wants_more_practice` is false).

### Topology Selection Guide

Use this table to match a domain to the right topology:

| Domain Pattern | Recommended Topology | Why |
|---|---|---|
| Step-by-step intake (medical, insurance, onboarding) | Linear with backtracking | Users need to go in order but may need to revise |
| Practice/tutoring (interview prep, language learning) | Iterative loop | Users repeat practice rounds until satisfied |
| Configuration wizard (product setup, trip planning) | Branching | Different paths based on early choices |
| Conditional depth (symptoms → detailed history if needed) | Progressive disclosure | Some phases are only relevant for certain users |
| Balancing tradeoffs (salary ↔ benefits, features ↔ timeline) | Negotiation / convergence | Two topics influence each other |
| Discovery/consultation (sales, general intake) | Free-form (hub and spoke) | Information arrives in unpredictable order |
| Simple form (survey, feedback, registration) | Linear | No backtracking needed, just collect and move on |

---

## Writing Good Purpose Statements

The `purpose` field is critical — it's what the Analyzer uses to detect cross-phase input. A good purpose statement is specific enough to distinguish this phase from every other phase.

**Bad — too vague:**
```json
"purpose": "Collect user information"
```
Why it fails: Multiple phases could match this. The Analyzer can't distinguish between phases.

**Bad — too detailed:**
```json
"purpose": "Collect the user's target company name (string, required), their specific role title (string, required), role seniority level (enum: junior/mid/senior/staff, required), and interview format (enum: coding/system_design/behavioral/phone_screen/full_loop, required), along with optional fields for interview date and recruiter topics."
```
Why it fails: This is the analyzer.md rewritten. It bloats the prompt and adds noise. The Analyzer already has the full skill file — the registry just needs enough to trigger detection.

**Good — specific and concise:**
```json
"purpose": "Collect details about the user's upcoming interview: company, role, level, and format."
```
Why it works: Specific enough to distinguish from other phases, concise enough to avoid clutter.

---

## Adding a New Phase

### Step 1: Create the phase entry

Add to `phase_registry.json` with display name, purpose, targets, conditions, and auto_advance setting.

### Step 2: Update incoming transitions

Find every phase that should be able to transition TO the new phase, and add it to their `allowed_targets` and `conditions`.

### Step 3: Verify no orphans

- [ ] At least one other phase can transition TO this phase (unless it's the `default_phase`)
- [ ] This phase can transition to at least one other phase (unless it's a terminal phase)
- [ ] The `default_phase` can still reach this phase through some transition path

### Step 4: Update dependent files

- [ ] Create `analyzer.md` and `speaker.md` in the skills folder
- [ ] Add the phase's fields to `state_schema.json`
- [ ] Update `orchestrator_rules.md` if the phase has custom transition conditions or business rules
- [ ] Regenerate the markdown summary for prompt injection
- [ ] Add test cases for the new phase

---

## Removing a Phase

### Step 1: Identify all references

Search for the phase name across: other phases' `allowed_targets` and `conditions`, `default_phase`, analyzer skill files (transition suggestions in other phases), orchestrator rules, and state schema.

### Step 2: Reroute transitions

For every phase that transitions TO the removed phase, update its targets to point to the appropriate replacement. Example: if removing phase_b from a chain `phase_a → phase_b → phase_c`, update phase_a to transition directly to phase_c.

### Step 3: Remove the entry

Delete the phase from the registry.

### Step 4: Clean up

- [ ] Remove or archive the phase's `analyzer.md` and `speaker.md`
- [ ] Decide whether to keep or remove the phase's fields from the state schema (they may be needed for historical data)
- [ ] Update orchestrator rules
- [ ] Remove test cases for the phase
- [ ] Verify no orphaned phases remain

---

## Renaming a Phase

Renaming is effectively removing + adding. The phase name is a key used across many files. Rename everywhere atomically:

1. Registry: phase key, all references in other phases' `allowed_targets` and `conditions`
2. Skills folder: rename the directory
3. State schema: update `phases` key
4. Orchestrator rules: update all references
5. Analyzer skill files: update transition suggestions in other phases
6. Test cases: update phase references

Use a find-and-replace across the entire project. The old name should appear zero times after the rename.

---

## Validation Checklist

Run these checks whenever the registry changes.

### Structural integrity
- [ ] Every phase has `display_name`, `purpose`, `allowed_targets`, and `conditions`
- [ ] `default_phase` exists in the `phases` object
- [ ] Every phase name uses `snake_case` with no spaces or special characters
- [ ] `auto_advance` is explicitly set for every phase (don't rely on defaults — be intentional)

### Transition integrity
- [ ] Every entry in `allowed_targets` references a phase that exists in the registry
- [ ] Every entry in `allowed_targets` has a corresponding entry in `conditions`
- [ ] No phase lists itself in `allowed_targets` (self-transitions are not meaningful)
- [ ] At least one terminal phase exists or at least one phase can become terminal via business rules
- [ ] The `default_phase` can reach every non-default phase through some transition path (no unreachable phases)

### auto_advance consistency
- [ ] Phases with `auto_advance: true` have at least one target with `all_required_complete` as the condition
- [ ] Phases with `auto_advance: true` and multiple targets also have a `default_next_phase` entry in orchestrator rules
- [ ] Interactive phases (practice, quizzes) have `auto_advance: false`

### Cross-artifact consistency
- [ ] Every phase in the registry has corresponding `analyzer.md` and `speaker.md` in the skills folder
- [ ] Every phase with skill files is registered in the registry
- [ ] Every phase in the registry has a corresponding entry in `state_schema.json`
- [ ] Every phase in the schema has a corresponding entry in the registry
- [ ] Transition targets in `analyzer.md` phase transition guidance match `allowed_targets` in the registry
- [ ] Every custom condition in `conditions` is documented in `orchestrator_rules.md`
- [ ] `default_next_phase` entries in orchestrator rules match phases in the registry

---

## Worked Example

### Domain: Mock Interview Agent

**Registry (`phase_registry.json`):**

```json
{
  "version": "1.0",
  "default_phase": "interview_setup",
  "phases": {
    "interview_setup": {
      "display_name": "Interview Setup",
      "purpose": "Collect details about the user's upcoming interview: company, role, level, and format.",
      "allowed_targets": ["question_practice"],
      "conditions": {
        "question_practice": "all_required_complete"
      },
      "max_turns": 10,
      "auto_advance": true,
      "order": 1
    },
    "question_practice": {
      "display_name": "Question Practice",
      "purpose": "Conduct mock interview questions tailored to the user's target role, company, and format. Collect responses and assess performance.",
      "allowed_targets": ["session_feedback", "interview_setup"],
      "conditions": {
        "session_feedback": "user_requests_advance",
        "interview_setup": "user_requests_backtrack"
      },
      "max_turns": 15,
      "auto_advance": false,
      "order": 2
    },
    "session_feedback": {
      "display_name": "Session Feedback",
      "purpose": "Collect the user's confidence level and determine whether they want more practice or are done.",
      "allowed_targets": ["question_practice"],
      "conditions": {
        "question_practice": "user_requests_advance"
      },
      "max_turns": 5,
      "auto_advance": false,
      "order": 3
    }
  }
}
```

**Transition map visualization:**

```
                    ┌──────────────────┐
                    │  interview_setup  │ (default, auto_advance)
                    └────────┬─────────┘
                             │ all_required_complete
                             ▼
                    ┌──────────────────┐
        ┌──────────│ question_practice │◄──────────┐
        │          └────────┬─────────┘            │
        │ user_requests_    │ user_requests_       │ user_requests_
        │ backtrack         │ advance              │ advance
        │                   │                      │
        ▼                   ▼                      │
┌──────────────────┐  ┌──────────────────┐         │
│  interview_setup  │  │session_feedback  │─────────┘
│  (restarts setup) │  │  [terminal if    │
└──────────────────┘  │   done=true]     │
                      └──────────────────┘
```

**Generated markdown summary (for Analyzer prompt injection):**

```markdown
## Phase Registry

### interview_setup — Interview Setup
Purpose: Collect details about the user's upcoming interview: company, role, level, and format.
Collects: target_company, role_title, role_level, interview_format
Optional: interview_timeline, technical_areas, preparation_level
Transitions to: question_practice (when all required complete)

### question_practice — Question Practice
Purpose: Conduct mock interview questions tailored to the user's target role, company, and format.
Collects: questions_completed
Transitions to: session_feedback (when user is ready), interview_setup (if user wants to go back)

### session_feedback — Session Feedback
Purpose: Collect the user's confidence level and determine whether they want more practice or are done.
Collects: feedback_acknowledged, wants_more_practice
Transitions to: question_practice (when user is ready)
```

The registry and schema work together: the registry says "interview_setup can transition to question_practice when all required fields are complete." The schema says "interview_setup's required fields are target_company, role_title, role_level, and interview_format." The Orchestrator reads both to make transition decisions.

---

## Customization Points

### Topology Selection

The choice of transition topology is the first major domain decision. Use this guide:

| Domain Pattern | Recommended Topology | Why |
|---|---|---|
| Step-by-step intake (medical, insurance, onboarding) | Linear with backtracking | Users need to go in order but may need to revise. |
| Practice/tutoring (interview prep, language learning) | Iterative loop | Users repeat practice rounds until satisfied. |
| Configuration wizard (product setup, trip planning) | Branching | Different paths based on early choices. |
| Discovery/consultation (sales, general intake) | Free-form (hub and spoke) | Information arrives in unpredictable order. |
| Simple form (survey, feedback, registration) | Linear | No backtracking needed, just collect and move on. |

### max_turns Calibration

| Phase Type | Recommended max_turns | Rationale |
|---|---|---|
| Simple collection (2–4 fields) | 8–10 | Users should complete quickly; a high turn count suggests confusion. |
| Complex collection (5–8 fields) | 12–15 | More fields need more turns, but still bounded. |
| Interactive (practice, exercises) | 15–20 | Users control pacing; set a generous but finite limit. |
| Wrap-up (feedback, confirmation) | 5 | Should be brief. |
| No limit needed | null | Only for truly open-ended phases. |

### auto_advance vs. Manual Advance

| Scenario | Setting | Why |
|---|---|---|
| All fields collected, one obvious next phase | `auto_advance: true` | Seamless progression, no dead air. |
| User should confirm before moving on | `auto_advance: false` | Give user control; Speaker summarizes and asks "shall we continue?" |
| Multiple possible next phases | `auto_advance: false` | Orchestrator needs business rules to pick the right branch. |
| User controls pacing (practice, exploration) | `auto_advance: false` | Let the user decide when they're done. |

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Phase exists in skills folder but not in registry | Analyzer can never detect it; Orchestrator can never transition to it | Always update registry and skills together |
| Vague `purpose` that overlaps with other phases | Analyzer falsely detects cross-phase input | Make purpose specific enough to uniquely identify the phase |
| Missing backtrack transitions | User gets stuck and can't correct earlier information | Add `user_requests_backtrack` transitions where appropriate |
| No terminal phase and no conditional exit | Orchestrator doesn't know when the workflow is done | Ensure at least one phase has empty `allowed_targets` or can become terminal |
| `allowed_targets` references a phase that doesn't exist | Orchestrator fails on transition | Run validation checklist after every change |
| Custom conditions not documented | Developer doesn't know how to implement them | Document every custom condition in `orchestrator_rules.md` |
| Overly permissive `always` conditions | User bounces between phases chaotically | Use `always` sparingly; prefer explicit conditions |
| `auto_advance: true` on a branching phase | Orchestrator picks whichever target comes first instead of the right branch | Set `auto_advance: false` on phases with multiple targets that depend on business logic |
| `auto_advance: true` without a `default_next_phase` rule | Auto-advance fires but Orchestrator doesn't know where to go | Every auto-advance phase needs a `default_next_phase` entry in orchestrator rules |
| Duplicating field lists in both registry and schema | Fields get out of sync; registry says one thing, schema says another | Fields live only in the schema. The summary generator pulls from the schema at runtime. |
| `purpose` that reads like an analyzer.md rewrite | Bloats the Analyzer prompt without adding detection value | Keep purpose to one sentence. The Analyzer has the full skill file for details. |
| Phase in schema but not in registry (or vice versa) | Orphaned config that confuses debugging | Run cross-artifact validation after any structural change |
