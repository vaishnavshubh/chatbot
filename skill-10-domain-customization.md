# Skill 10: Domain Customization

## Purpose

This skill defines the process for taking a set of **domain requirements** (what the agent should do) and generating a complete, deployable multi-phase conversational agent. It is the meta-level skill — the skill for generating all the other generated artifacts (phase skills, state schema, phase registry, orchestrator rules).

This is the skill the system author uses. Every other skill is either a framework skill (reusable across domains) or a generated skill (produced by this process for a specific domain). This skill bridges the two.

---

## Core Principles

1. **Domain requirements in, working agent out.** The input is a natural-language description of what the agent should accomplish. The output is a complete set of configuration files, phase skills, state schema, and orchestrator rules — everything needed to plug into the framework and start a conversation.
2. **Plan first, generate second.** Don't jump straight to artifact generation. Produce a concrete plan, surface the decisions that could go either way, and confirm before committing to the full build. People are dramatically better at reacting to a proposal than answering abstract questions.
3. **Phases emerge from the task, not from a template.** Don't start with a fixed number of phases and try to fill them. Analyze what information needs to be collected, in what order, with what dependencies, and let the phases fall out naturally.
4. **Every field earns its place.** Don't add fields "just in case." Every field in the schema should correspond to something the agent demonstrably needs to collect or track to accomplish its purpose.
5. **The generated artifacts are the first draft, not the final product.** This process produces a high-quality starting point. Domain experts should review and refine the output, especially the phase skills (analyzer.md and speaker.md), which encode the conversational behavior.
6. **Consistency across artifacts is non-negotiable.** Field names in the schema must match field names in analyzer.md. Phase names in the registry must match folder names in the skills directory. Transition targets must reference real phases. This process validates cross-artifact consistency as a final step.

---

## Input: Domain Requirements

The domain requirements document describes what the agent should do. It can range from a single paragraph to a detailed specification. The generation process extracts what it needs from whatever level of detail is provided.

### Minimum Viable Requirements

At minimum, the requirements must answer:

1. **What is the agent's purpose?** (one sentence)
2. **What information does it need to collect?** (list of data points)
3. **What does it do with the collected information?** (output/action)

### Ideal Requirements Document

A complete requirements document includes:

```markdown
# Agent: [Name]

## Purpose
[One paragraph describing what the agent does and why]

## Target Users
[Who will interact with this agent]

## Information to Collect
[List of all data points, grouped by topic]
- Group A: [topic]
  - field 1: [description, any constraints]
  - field 2: [description, any constraints]
- Group B: [topic]
  - field 3: ...

## Workflow
[How the conversation should flow]
- Start with: [what to ask first and why]
- Then: [next stage]
- Finally: [conclusion]

## Constraints
- [Any ordering requirements]
- [Any conditional logic]
- [Any validation rules]
- [Maximum conversation length expectations]

## Tone and Style
- [Formal/casual/technical/friendly]
- [Any domain-specific language requirements]
- [Any things to avoid saying]

## Edge Cases
- [What if the user doesn't know X?]
- [What if the user provides contradictory info?]
- [What if the user wants to skip something?]

## Output
- [What happens when collection is complete?]
- [What format should the final data be in?]
```

---

## Generation Process

The generation process has seven stages. The first two stages — planning and confirming — ensure the right thing gets built before committing to the full artifact generation pipeline.

```
Requirements Document
        │
        ▼
┌──────────────────────┐
│ Stage 1: Plan        │  → Concrete proposal with explicit assumptions
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Stage 2: Confirm     │  → Targeted clarifications, user approval
│   & Clarify          │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Stage 3: Analyze     │  → Information groups, dependencies, workflow
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Stage 4: Design      │  → Phase definitions, field assignments
│   Phases             │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Stage 5: Build       │  → state_schema.json, phase_registry.json,
│   Config             │    orchestrator_rules.md, prompts/*.md
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Stage 6: Write       │  → analyzer.md + speaker.md per phase
│   Phase Skills       │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Stage 7: Validate    │  → Cross-artifact consistency check
│   & Test             │
└──────────────────────┘
```

### Skill Dependencies

This process draws on Skills 1–10 at different stages. Before generating artifacts for a new domain, consult the relevant skills so the output aligns with what the framework expects.

| Skill | Name | Consulted During | Why |
|-------|------|-----------------|-----|
| **1** | Phase Skill Authoring | Stage 6 (Write Phase Skills) | Defines the templates, structure, and craft guidance for analyzer.md and speaker.md files. The canonical reference for what goes in each file. |
| **2** | Analyzer Prompt Engineering | Stages 5–6 (Build Config, Write Phase Skills) | Defines the framework prompt template that wraps analyzer.md at runtime. Consulted during Stage 5 to copy and optionally customize `prompts/analyzer_template.md` for the domain (see Customization Points in Skill 2). Consulted during Stage 6 to understand what global extraction rules the template already provides, so phase skills don't duplicate them. |
| **3** | Speaker Prompt Engineering | Stages 5–6 (Build Config, Write Phase Skills) | Defines the framework prompt template that wraps speaker.md at runtime. Consulted during Stage 5 to copy and optionally customize `prompts/speaker_template.md` for the domain (see Customization Points in Skill 3). Consulted during Stage 6 to understand what global communication rules and turn types the template already provides. |
| **4** | State Schema Design | Stage 5 (Build Config) | Defines the schema format, field types, update policies, and validation rules. Use it to ensure the generated state_schema.json follows framework conventions. |
| **5** | Phase Registry Design | Stage 5 (Build Config) | Defines the registry format, transition conditions, transition topologies, and phase graph conventions. Use it to ensure the generated phase_registry.json is valid. |
| **6** | Orchestrator Rules Authoring | Stage 5 (Build Config) | Defines the format and semantics of orchestrator_rules.md — transition confidence, default flow, cross-phase context, business rules, conversation limits, execution loop configuration (hooks, error tolerance, fallback messages). |
| **7** | Conversation History Management | Stage 5 (Build Config) | Defines how conversation history is managed: cumulative summary plus recent unsummarized turns. Covers per-component history formatting (Analyzer view vs. Speaker view) and the summary prompt template (`prompts/summary_template.md`). Consulted during Stage 5 to copy and optionally customize `prompts/summary_template.md` for the domain. |
| **8** | Error Recovery and Graceful Degradation | Stages 5–6 (Build Config, Write Phase Skills) | Defines the error catalog, recovery strategies, severity levels, and user behavior recovery (off-topic handling, refusals, contradictions). Informs error tolerance thresholds and fallback message configuration in orchestrator rules. Also informs edge case handling in phase skill files. |
| **9** | Testing and Debugging | Stage 7 (Validate & Test) | Defines the pre-deployment validation checks, functional test case categories, runtime debugging approaches, and continuous monitoring. Use it to verify cross-artifact consistency and build the test suite. |

**How to use this table:** At each stage, read the relevant skills before generating artifacts. Skills 4–7 are most critical during Stage 5 (config generation and prompt template setup). Skills 2–3 are also consulted during Stage 5 for prompt template customization, and are most critical during Stage 6 (phase skill writing) alongside Skill 1. Skill 8 informs both Stage 5 (error configuration) and Stage 6 (edge case handling in skills). Skill 9 drives Stage 7 validation.

---

## Stage 1: Plan

Even from incomplete requirements, produce a concrete first-draft plan. Don't ask a list of abstract questions — generate a proposal the user can react to.

### Threshold Rule

If you can generate a plan that's at least 60% likely to be directionally correct, generate it. If requirements are too vague for even a rough plan (e.g., "I want a chatbot for my business"), ask 2–3 high-level scoping questions first — but this is the exception, not the default.

### Plan Output Format

```markdown
## Phase Overview
| Phase | Purpose | Required Fields | Transitions To |
|-------|---------|-----------------|----------------|
| ... | ... | ... | ... |

## Transition Map
(visual or tabular representation of allowed transitions)

## Assumptions Made
- (numbered list of assumptions made to fill gaps)

## Decisions Needing Your Input
- (numbered list with concrete options anchored to the plan)
```

### What to Highlight for User Input

Present decisions that could go either way as concrete choices:

- **Structural decisions:** "I split 'collecting user info' into two phases: basic profile and preferences. I could also keep it as one. Which do you prefer?"
- **Field decisions:** "I made 'preferred_method' required. Should it be optional with a default assumption?"
- **Transition decisions:** "Should the user be able to skip the 'preferences' phase, or is it mandatory?"
- **Tone decisions:** "Should the agent be formal, conversational, or match the user's tone?"

Use concrete options anchored to the plan the user can already see. Never ask questions in the abstract when you can ask them in context.

---

## Stage 2: Confirm and Clarify

Present the plan and targeted clarifications together. Don't just dump the plan — highlight the specific decisions and wait for feedback.

### Response Handling

- **User approves:** Proceed to Stage 3.
- **User tweaks:** Fold minor changes in and acknowledge. No need to re-present the full plan.
- **User significantly restructures:** Update the plan and re-present for confirmation.

Once the plan is confirmed, the remaining stages execute against the confirmed design.

---

## Stage 3: Analyze Requirements

Read the confirmed plan and requirements and produce a structured analysis.

### Process

1. **Identify all data points** mentioned in the requirements. Every piece of information the agent needs to collect becomes a candidate field.
2. **Group data points** by topic or conversation stage. Groups that are naturally discussed together become candidate phases.
3. **Map dependencies.** Which fields depend on other fields? Which fields must be collected before others? Dependencies determine phase ordering and transition conditions.
4. **Identify derived vs. collected fields.** Some fields are collected from the user. Others are computed, inferred, or tracked automatically by the system. Only collected fields go in the Analyzer's scope.
5. **Note constraints.** Required vs. optional, enum values, validation rules, conditional logic.
6. **Identify entity structures.** Some phases collect the same set of fields multiple times for different instances — multiple work projects, multiple symptoms, multiple products. When a group of fields naturally repeats for N entities, mark the group as entity-bearing. Identify: what constitutes one entity, which fields are per-entity vs. phase-level, and what triggers rotation to the next entity. See Skill 4's Entity-Bearing Phases section for when entity structure is appropriate vs. when a simple `string[]` field suffices.
7. **Identify the workflow shape.** Is it linear (A → B → C)? Branching (A → B or C)? Looping (A → B → A)? The shape determines the phase graph.

### Output: Requirements Analysis

```yaml
agent_name: "..."
purpose: "..."  # one sentence from the requirements

data_points:
  - name: field_name              # snake_case, descriptive
    description: "..."            # what this field captures
    source: user_collected         # or system_tracked, derived
    required: true                 # or false
    type: string                   # string, integer, boolean, enum, string[]
    # values: [a, b, c]           # include only for enum types
    group: group_name              # which candidate group this belongs to
    dependencies: []               # fields that must exist before this one
    # constraints:                 # include only if the domain imposes rules
    #   - "description of constraint"
    # entity_scope: phase_level    # or per_entity — only relevant for entity-bearing groups

  # Repeat for every data point identified in the requirements.
  # Include system-tracked and derived fields — mark their source
  # accordingly so Stage 4 knows not to put them in the Analyzer's scope.

candidate_groups:
  - name: group_name
    fields: [field_a, field_b, field_c]
    natural_order: 1               # conversation sequence position
    # depends_on: [other_group]    # include only if this group requires prior groups

  # Groups that are naturally discussed together become candidate phases.
  # Dependencies between groups determine phase ordering.

entity_structures:                   # OPTIONAL — omit if no groups are entity-bearing
  - group: group_name                # which candidate group this applies to
    entity_name: "project"           # what one entity is called (singular noun)
    per_entity_fields: [field_a, field_b]
    phase_level_fields: [field_c]    # fields collected once for the whole phase
    min_entities: 1
    max_entities: 5                  # null if unbounded (but must have exit condition)
    rotation_trigger: "after_core_questions_answered | user_initiated | time_based"
    rotation_description: "Move to next project after role, name, and key contribution are collected, or when user says they want to discuss another project."

workflow_shape: linear | branching | iterative_loop | progressive_disclosure | negotiation
  # See Skill 5 (Phase Registry) Transition Topologies for shape definitions.
  # Add a comment describing the specific flow, e.g.:
  # setup → activity ↔ feedback → summary

constraints:
  - "..."  # Domain-specific ordering, validation, or conditional rules

tone: "..."  # From the requirements or inferred from target audience
```

**Guidelines for this stage:**

- Every piece of information the agent collects, tracks, or derives should appear as a data point. If it's not here, it won't make it into the schema.
- Mark `source` accurately — only `user_collected` fields go in the Analyzer's extraction scope. `system_tracked` and `derived` fields are managed by the engine or computed from other fields.
- Dependencies drive phase ordering. If field B can't be collected until field A exists, that's a dependency. If they're independent, don't add a false dependency.
- Choose `workflow_shape` based on the actual task flow, not by defaulting to the simplest option. Review Skill 5's Transition Topologies section if the shape isn't obvious.
- Not every phase has entities. Most phases collect a flat set of fields once. Only mark a group as entity-bearing when the user genuinely provides multiple instances of the same structure (e.g., "tell me about your projects" where each project has a name, role, and technologies). Don't force entity structure onto phases where a simple list field (`string[]`) would suffice. See Skill 4's Entity-Bearing Phases section for the decision criteria.

---

## Stage 4: Design Phases

Convert candidate groups into phases with defined boundaries, transitions, and responsibilities.

### Decision Rules

**When to make a group its own phase:**
- It has 3+ fields that are naturally discussed together
- It has a clear entry condition ("after X is done, start Y")
- Its conversational tone or style differs from adjacent groups
- It represents a distinct mode of interaction (collecting info vs. running an exercise vs. giving feedback)

**When to merge groups into one phase:**
- They have fewer than 3 fields combined
- They are always discussed in the same breath
- Splitting them would create an awkward transition
- They share the same conversational mode

**When to split a group into multiple phases:**
- It has 6+ fields and collecting them all at once feels overwhelming
- Some fields are conditionally needed (split conditional fields into a sub-phase)
- The group contains both "setup" fields and "execution" fields

**When to use entity structure:**
- The same set of 2+ fields is collected for multiple instances
- Users naturally provide these instances one at a time in conversation
- The agent needs to steer between instances ("Tell me about your next project")

**When NOT to use entity structure:**
- A simple `string[]` append field captures what's needed (e.g., a list of skills)
- The "instances" don't have internal structure (just names or labels)
- There's always exactly one instance

### Phase Naming Conventions

- Use `snake_case`
- Use descriptive names that reflect the phase's purpose
- Avoid generic names like `phase_1`, `step_2`
- Good: `patient_intake`, `symptom_assessment`, `treatment_plan`, `order_setup`, `preference_collection`
- Bad: `phase_1`, `info_collection`, `main`, `step_2`

### Output: Phase Design

```yaml
phases:
  - name: phase_name              # snake_case, descriptive (see naming conventions above)
    purpose: "..."                 # one sentence: what this phase accomplishes
    fields:
      - field_a                    # required — annotate each field
      - field_b                    # required
      - field_c                    # optional
      - field_d                    # system-tracked (not extracted by Analyzer)
    entry_condition: "..."         # "default (first phase)" or "previous_phase complete"
    exit_condition: "..."          # what must be true to leave this phase
    allowed_transitions:
      to: [next_phase_a, next_phase_b]  # all valid targets
      conditions:
        next_phase_a: "all_required_complete"
        next_phase_b: "user_requests_advance"
    # entity_config:                 # OPTIONAL — omit entirely for non-entity phases
    #   entity_name: "project"
    #   per_entity_fields: [field_a, field_b]
    #   phase_level_fields: [field_c]
    #   min_entities: 1
    #   max_entities: 5
    #   rotation_rule: "after_core_questions_answered"
    #   exit_condition: "user signals no more entities, or max reached"
    # notes: "..."                 # include only if this phase has unusual behavior
                                   # (e.g., interactive mode, conditional terminal state)

  # Repeat for every phase.
  # Typical agents have 2–5 phases. Fewer than 2 means the task is too simple
  # for multi-phase orchestration. More than 5 is a smell — look for phases to merge.
```

### Phase Graph Visualization

Always produce an ASCII graph showing the phase flow. Use boxes for phases, arrows for transitions, and annotate transition conditions. The graph should make the workflow shape immediately obvious.

```
┌──────────────┐
│  phase_one   │
│  (N required)│
└──────┬───────┘
       │ condition
       ▼
┌──────────────┐    ┌──────────────┐
│  phase_two   │───▶│  phase_three │
└──────────────┘    └──────────────┘
```

Match the graph to the workflow shape identified in Stage 3. Skill 5's Transition Topologies section provides reference graphs for all supported shapes.

Entity-bearing phases should be annotated in the graph with the entity type and count:

```
┌──────────────────────┐
│  experience_review   │
│  (entity: project)   │
│  (2 required, max 5) │
└──────────┬───────────┘
```

---

## Stage 5: Build Config (Schema, Registry, and Rules)

Convert the phase design into the three configuration artifacts.

### State Schema

#### Schema Generation Rules

1. **One entry per field per phase.** Every field appears under its owning phase.
2. **Type mapping:** String → `"string"`, integer → `"integer"`, boolean → `"boolean"`, list of strings → `"string[]"`, enum → `"enum: val1 | val2 | val3"`.
3. **Required fields** get `"required": true`. Optional fields get `"required": false`.
4. **Update policy defaults:** Most fields use `"overwrite"`. List fields use `"append"`. Fields where contradictions matter use `"conflict"`.
5. **Display names** are the human-readable labels the Speaker will use instead of field names.
6. **Defaults** are set for system-tracked fields (e.g., a counter field defaults to `0`).
7. **Entity-bearing phases** use the extended format from Skill 4's Entity-Bearing Phases section with `entity_config`, `per_entity_fields`, and `phase_level_fields`. Non-entity phases keep the flat structure unchanged.

#### Update Policy Definitions

- **overwrite**: New value replaces old. Use for most single-value fields. Handles user corrections naturally ("actually it's mid-level, not senior").
- **append**: New values merge into an existing array. Use for list-type fields. Handles additive input ("also distributed systems").
- **conflict**: Store both values and flag for clarification. Use sparingly — only for fields where contradictions indicate genuine confusion, not simple corrections. Example: user says "Google" in one turn and "Amazon" in another without indicating a change.

#### Output: state_schema.json
```json
{
  "version": "1.0",
  "phases": {
    "phase_name": {
      "string_field": {
        "type": "string",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Human-Readable Label",
        "description": "What this field captures, in plain language."
      },
      "enum_field": {
        "type": "enum: option_a | option_b | option_c",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Human-Readable Label",
        "description": "What this field captures, in plain language."
      },
      "list_field": {
        "type": "string[]",
        "required": false,
        "update_policy": "append",
        "default": [],
        "display_name": "Human-Readable Label",
        "description": "What this field captures, in plain language."
      },
      "integer_field_with_validation": {
        "type": "integer",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Human-Readable Label",
        "description": "What this field captures, in plain language.",
        "validation": {
          "min": 1,
          "max": 10
        }
      },
      "system_tracked_field": {
        "type": "integer",
        "required": false,
        "update_policy": "overwrite",
        "default": 0,
        "display_name": "Human-Readable Label",
        "description": "What this field captures, in plain language."
      }
    }
  }
}
```

**Key decisions when building the schema:**
- `display_name` is what the Speaker sees for collected data. Make it natural language — "Preferred contact method" not "preferred_contact_method." Every field needs one.
- `description` is what the Speaker sees when listing missing fields. Write it as a sentence fragment that could be shown as a question topic — "The company where the user is interviewing." Every field needs one.
- `update_policy` defaults to `"overwrite"` for most fields. Use `"append"` for list-type fields where users add items incrementally. Use `"conflict"` sparingly — only when contradictions indicate genuine confusion, not simple corrections.
- `validation` is optional. Add it for fields with meaningful bounds (ratings, counts, dates). Don't add it for free-text strings.
- `default` is `null` for most fields (meaning "not yet collected"). Use `[]` for array fields so append works without null checks. Do not use `0` or `false` as defaults for fields where those are meaningful collected values.
- `entity_config` is only present for entity-bearing phases. Its `rotation_rule` must match a rule in the orchestrator_rules.md Entity Rotation Rules section. The `display_name` is how the Speaker refers to the entity type ("Let's discuss your next work project").
- `per_entity_fields` are collected once per entity instance. They reset (empty) when rotating to a new entity. `phase_level_fields` are collected once for the whole phase and persist across entity rotations.
- For entity-bearing phases, phase completion requires: all per-entity required fields filled for the current entity, `min_entities` met, AND any phase-level required fields filled.

### Phase Registry
```json
{
  "version": "1.0",
  "default_phase": "first_phase_name",
  "phases": {
    "first_phase_name": {
      "display_name": "Human-Readable Phase Name",
      "purpose": "One sentence describing what this phase does, specific enough for cross-phase detection.",
      "allowed_targets": ["second_phase_name"],
      "conditions": {
        "second_phase_name": "all_required_complete"
      },
      "max_turns": 10,
      "auto_advance": true
    },
    "second_phase_name": {
      "display_name": "Human-Readable Phase Name",
      "purpose": "One sentence describing what this phase does, specific enough for cross-phase detection.",
      "allowed_targets": ["third_phase_name"],
      "conditions": {
        "third_phase_name": "user_requests_advance"
      },
      "max_turns": 15,
      "auto_advance": false
    }
  }
}
```

**Key decisions when building the registry:**
- `default_phase` is where every conversation starts. It must exist in `phases`.
- `purpose` is a one-sentence description of what the phase does. The Analyzer uses it for cross-phase detection, so it must be specific enough to distinguish this phase from every other phase. Don't restate the full analyzer.md — just enough to trigger detection.
- `allowed_targets` defines the full set of phases reachable from this one. Every target must exist as a key in `phases`.
- `conditions` maps each target to a transition condition: `"all_required_complete"` (auto-advance when all required fields are filled), `"user_requests_advance"` (advance only when the user signals readiness), or a custom condition name defined in orchestrator rules.
- `max_turns` is a safety limit per phase, not a target. Set it generously enough to allow natural conversation but tight enough to catch loops. Collection phases: 5–10. Interactive phases: 10–20. Feedback phases: 3–5. Use `null` for truly open-ended phases with no turn limit.
- `auto_advance`: `true` means the State Updater transitions automatically when the condition is met. `false` means the Speaker confirms with the user first. Use `true` for straightforward collection phases, `false` for phases where the user might want to linger or where multiple targets require business logic to choose between.


### Orchestrator Rules

The orchestrator rules are written in plain English markdown so they're readable by both humans and LLMs without needing a parser. The engine reads this file and interprets the rules at runtime.

**Before writing this file, read Skill 6 (Orchestrator Rules Authoring).** Skill 6 is the canonical reference for the template, section-by-section guidance, BAD/GOOD examples, and craft principles. Follow its template exactly.

Every `orchestrator_rules.md` must include all of the following sections:

1. **Transition Confidence** — Minimum confidence threshold (default 0.7; raise for high-stakes, lower for casual domains)
2. **Default Phase Flow** — One line per non-terminal phase: `After [source] → go to [target]`
3. **Cross-Phase Context** — Per target phase: which fields to carry forward from which source phases. Only include fields the Speaker actually needs.
4. **Business Rules** — Named rules with specific conditions and actions. Three types: transition blockers, transition forcers, state modifiers. Every domain constraint from the requirements should appear here.
5. **Entity Rotation Rules** — For entity-bearing phases: rotation trigger, cross-entity context, exit condition, and minimum entities. Omit or write "No entity-bearing phases" if none exist. See Skill 6.
6. **Conversation Limits** — Global turn limit and inactivity timeout
7. **Hooks** — Extension points at four pipeline stages: pre-conversation, mid-pipeline, post-completion, pre-resumption. Write "none" explicitly for unused hooks.
8. **Error Tolerance** — Max retries per component, consecutive error threshold, and escalation action (alert, terminate, or switch_model). See Skill 8.
9. **Fallback Messages** — One domain-appropriate message per turn type (first_turn, standard, phase_transition, clarification, entity_transition) plus a termination message with next-step guidance.
10. **Resumption** — Whether abandoned conversations can resume, and the TTL for persisted state.

**Key principles:**

- Business rules should be specific and testable. "Handle edge cases appropriately" is not a rule. "Block transition to X if Y has not been collected" is.
- Cross-phase context should be minimal. Only pass fields the Speaker would sound wrong without.
- Every loop must have an exit condition.
- Confidence threshold, error tolerance, and escalation action should align with the domain's risk level.
- Every field name must match `state_schema.json` exactly. Every phase name must match `phase_registry.json` exactly.
- Entity rotation rules must have explicit exit conditions. "Continue until done" is not an exit condition. "User says no more projects, or 5 projects discussed" is.
- Cross-entity context should be minimal — just enough for the Speaker to reference prior entities naturally. Don't carry full entity data forward.

### Prompt Templates

Copy the three framework prompt templates into the `prompts/` directory:

- `prompts/analyzer_template.md` — from Skill 2 (Analyzer Prompt Engineering)
- `prompts/speaker_template.md` — from Skill 3 (Speaker Prompt Engineering)
- `prompts/summary_template.md` — from Skill 7 (Conversation History Management)

**Most domains use these templates as-is.** However, if the domain requires different extraction or communication behavior, customize them during this stage:

- **Analyzer template customization** (see Skill 2, Customization Points): Modify the Global Rules section for domains that need different extraction defaults (e.g., "infer missing values from context," "all dates must be in ISO format") or modify the Output Format for domains that need additional signals (e.g., `sentiment`, `urgency`).
- **Speaker template customization** (see Skill 3, Customization Points): Modify global communication rules, turn type behavior, or data formatting for domains with different conversational needs.
- **Summary template customization** (see Skill 7): Adjust the summarization prompt if the domain requires different history condensation behavior.

If no customization is needed, copy the templates verbatim. Either way, the `prompts/` directory must be populated during this stage so that Stage 6 (Write Phase Skills) can reference what the templates already provide.

---

## Stage 6: Write Phase Skills

This is the most critical stage. Each phase gets two skill files — `analyzer.md` and `speaker.md` — that are injected into framework prompt templates at runtime. They directly control extraction accuracy and conversational quality.

### How the pieces fit together

Three skills work together to produce working prompts. Understanding the relationship matters:

| Skill | What it defines | Artifact |
|-------|----------------|----------|
| **Skill 1** (Phase Skill Authoring) | Templates and craft guidance for writing per-phase content | `skills/{phase}/analyzer.md`, `skills/{phase}/speaker.md` |
| **Skill 2** (Analyzer Prompt Engineering) | The framework prompt template that wraps analyzer.md at runtime | `prompts/analyzer_template.md` |
| **Skill 3** (Speaker Prompt Engineering) | The framework prompt template that wraps speaker.md at runtime | `prompts/speaker_template.md` |

At runtime, the engine loads a framework template (Skill 2 or 3), injects the phase-specific content (Skill 1) into it via placeholders, adds state and history context, and sends the assembled prompt to the LLM. The phase skill files never run alone — they always operate inside their framework template.

This means:

- **Don't duplicate what the template already provides.** Skill 2's template already includes global extraction rules ("extract only what's explicit," "output must be valid JSON," "do not include text outside the JSON"). Skill 3's template already includes global communication rules ("never mention field names," "ask one question per turn," "acknowledge before asking"). Phase skill files should not repeat these — they should add phase-specific detail on top.
- **Don't omit what the template expects.** Skill 2's template expects analyzer.md to define fields, extraction examples, cross-phase detection, and completion criteria. Skill 3's template expects speaker.md to provide role, tone, opening message, questioning strategy, and edge cases. If a phase skill is missing a section the template references, the LLM gets an incomplete instruction set.
- **Know the turn type system.** Skill 3 defines five turn types — `first_turn`, `standard`, `phase_transition`, `clarification`, and `entity_transition` — each with different context injected into the prompt. The speaker.md Opening Message section is used specifically on `first_turn` and `phase_transition` turns. Write opening guidance knowing it will be triggered in these contexts, not on every turn.

### How to write them

Use **Skill 1** for the templates and craft guidance — it is the canonical reference for analyzer.md and speaker.md structure, content quality, and anti-patterns.

Read **Skill 2** to understand what the analyzer framework template already provides (global extraction rules, output format, structured output enforcement) so you don't duplicate it in analyzer.md files.

Read **Skill 3** to understand what the speaker framework template already provides (global communication rules, turn type system, data formatting) so you don't duplicate it in speaker.md files.

This stage's job is to:

1. **Assign fields to files.** Use the phase design from Stage 4 to determine which fields go in each phase's analyzer.md.
2. **Provide domain context.** Fill Skill 1's template with the domain-specific content — field names, types, extraction examples, tone, questioning order, edge cases — that came out of Stages 3–5.
3. **Ensure schema alignment.** Every field name, type, and required/optional flag in analyzer.md must exactly match the state schema from Stage 5. Every transition target must exist in the phase registry.

### What goes in each file

**analyzer.md** — Phase-specific extraction instructions, injected into Skill 2's template via `{{active_phase_analyzer_md}}`:
- What fields to look for, with types and examples
- How to handle ambiguity (when to extract, when to leave null)
- When to suggest a phase transition (cross-phase detection)
- When the phase is complete (explicit field checklist)
- **Phase-change signaling quality:** Cross-phase detection examples should be accurate — clear positive and negative examples. A negative example shows something that *looks like* another phase but isn't. False positives cause unnecessary phase redirect passes (extra LLM calls), so invest in good examples.
- **Entity-aware extraction:** For entity-bearing phases, the analyzer.md must specify that extracted per-entity fields apply to the current entity. The framework handles entity indexing — the analyzer.md just needs to define what fields to look for and how to detect when the user is introducing a new entity instance (e.g., "I also worked on..." or "Another project was..."). Include 2–3 examples of entity-introduction detection and 1–2 negative examples (mentions that look like new entities but aren't). Important: entity-switch detection should NOT use `phase_suggestion` — it's handled by the State Updater, not as a phase change.
- Does NOT need to restate: output format, global extraction rules, or "extract only explicit" — Skill 2's template already provides these.

**speaker.md** — Phase-specific communication guidance, injected into Skill 3's template via `{{active_phase_speaker_md}}`:
- Role and tone for this phase
- What to say on the opening turn (no user message yet)
- How to ask for missing fields (priority order, natural phrasing)
- How to acknowledge what the user provided
- How to wrap up when everything is collected
- What never to say (domain-specific prohibitions)
- **Entity rotation handling:** For entity-bearing phases, the speaker.md must provide guidance for:
  - **Entity transition messages:** How to naturally move from one entity to the next ("That's great context on Project Alpha. Do you have another project you'd like to discuss?")
  - **Cross-entity references:** How to reference prior entities briefly without repeating all collected data ("In addition to the backend work on Project Alpha...")
  - **Entity completion:** How to signal that enough entities have been discussed and the phase is wrapping up
  - **Opening after rotation:** What the first message for entity N+1 should sound like (lighter than the phase opening since rapport is established)
- Does NOT need to restate: "never mention field names," "ask one question per turn," "no JSON in output" — Skill 3's template already provides these as global rules. Phase-specific "never do" items (like "never recommend products during intake" or "never give diagnoses during symptom collection") still belong here.

### Practical guidance

- Not every field needs every sub-bullet from Skill 1's template. Use the ones that add clarity — skip the ones that would be redundant for a given field.
- Analyzer quality depends most on **examples** and **"Do NOT extract" rules**. Skimp on those and extraction accuracy drops.
- Speaker quality depends most on **demonstrated tone** (good/bad phrasing examples) and **opening message guidance**. A weak opening sets the wrong tone for the entire conversation.
- When in doubt about how to write a section, check Skill 1's Part 3 (craft guidance) for BAD/GOOD comparison examples.
- When in doubt about what the surrounding template already handles, check Skill 2 (analyzer template) or Skill 3 (speaker template) before adding instructions to a phase skill file.

### What makes a good analyzer.md

The quality of an analyzer.md file depends on three things, roughly in order of impact:

1. **Extraction examples.** Every field needs 3–5 examples showing realistic user input mapped to the extracted value. Include at least one "Do NOT extract" example per field showing what *looks like* the field but shouldn't be extracted (ambiguous input, past tense, hypothetical, etc.). Without these, the LLM guesses — and guesses wrong on edge cases.

2. **"Do NOT extract" rules.** Explicit boundaries for each field. What's close but wrong? What's ambiguous enough to leave null? These prevent false positives, which are worse than false negatives (a wrong value is harder to recover from than a missing one).

3. **Cross-phase detection examples.** Concrete user utterances mapped to phase suggestions. Not just "if the user wants to move on" — actual phrases like *"Can we start?"* → `phase_suggestion: "next_phase"`.

4. **Entity-switch detection examples** (for entity-bearing phases). Concrete user utterances mapped to entity-switch signals. Not just "if the user mentions a new project" — actual phrases like *"I also worked on a data pipeline"* → extract as new entity, *"That same project also involved..."* → continue current entity. Include negative examples: *"My team built a pipeline"* (referencing current project's detail, not a new project).

**Common weaknesses to avoid:**

- Vague extraction guidance: "Extract the user's preference" doesn't tell the LLM *how*. Show the mapping with examples.
- Missing enum synonyms: If a field is `enum: formal | casual | technical`, users will say "relaxed," "chill," "buttoned-up." Map synonyms explicitly in an **Interpretation** section.
- Over-extracting: Not every mention of a concept is an extraction. If the user asks "What does X mean?" that's a question, not a data point. Add a rule for it.
- Completion criteria that forget optional fields: Completion should check only required fields. State this explicitly: "Optional fields do NOT affect completion."

### What makes a good speaker.md

The quality of a speaker.md file depends on:

1. **Demonstrated tone.** Don't just say "be friendly" — show what friendly sounds like in this domain. Provide example phrasings for acknowledgments, questions, and transitions. Include BAD examples that show what the wrong tone looks like (too formal, too stiff, too verbose).

2. **Opening message guidance.** The opening message sets the tone for the entire conversation. Provide a concrete example and explicit "Do NOT" rules (e.g., don't list all fields upfront, don't give a disclaimer).

3. **Questioning strategy with priority order.** Which field to ask for first isn't arbitrary — it should follow domain logic (ask for the thing that most affects subsequent questions first). Number the priority order and explain why.

4. **Edge case responses.** Real users don't follow the happy path. Provide scripted responses for common deviations: user doesn't know the answer, user provides everything at once, user asks a counter-question, user gets frustrated. Each edge case should include a concrete example response.

5. **Entity rotation flow** (for entity-bearing phases). The Speaker needs clear guidance on transitioning between entities within a phase. This is different from phase transitions — the tone stays the same, but the Speaker needs to close out one entity and open the next. Provide concrete example messages for the transition. Bad: "Moving on to your next project." Good: "Thanks for walking me through that. Is there another project you'd like to highlight?"

**Common weaknesses to avoid:**

- Generic tone guidance: "Be professional and helpful" applies to every agent. What's specific to *this* domain? A medical intake agent and a travel planning agent are both "helpful" but sound completely different.
- Missing "Things to NEVER Do" section: Every speaker.md needs domain-specific prohibitions. Never mention field names. Never say "required fields." Never reference phase names. Never use jargon the user wouldn't know.
- Acknowledgments that parrot everything back: "So you said X and Y and Z" is robotic. Good acknowledgments are brief and move forward: "Got it — X. And what about Y?"
- Transition messages that feel abrupt: When all fields are collected, the speaker should briefly summarize (hitting highlights, not listing everything) and signal readiness for the next phase.

---

## Stage 7: Validate and Test

### Cross-Artifact Consistency Checks

Run these checks after generating all artifacts. Every failure must be fixed before the agent is usable.

**Phase alignment:** Every phase in the registry must exist in the schema, and vice versa. If a phase appears in one but not the other, something was missed during generation.

**Transition validity:** Every `allowed_targets` entry in the registry must reference a phase that actually exists. A transition pointing to a non-existent phase will crash at runtime.

**Default phase existence:** The `default_phase` in the registry must be a valid phase key. If it's misspelled or missing, the agent can't start a conversation.

**Skill file completeness:** Every phase in the registry must have both `analyzer.md` and `speaker.md` in its skills directory. A missing file means the framework template has nothing to inject, producing an incomplete prompt.

**Cross-phase field references:** Every field referenced in the orchestrator rules' cross-phase context section must exist in the source phase's schema. If the rules say "pass `field_x` from phase_a to phase_b" but `field_x` isn't in phase_a's schema, the engine will try to pass a value that doesn't exist.

**Reachability:** Every phase must be reachable from the default phase by following transition paths. An unreachable phase is dead code — it was defined but no transition path leads to it. Walk the graph from the default phase and flag any phase not visited.

**Terminal existence:** At least one phase must be able to end the conversation. This could be a phase with an empty `allowed_targets` list, or a phase with a conditional exit (like a loop that terminates when a field is false). Without a terminal condition, the conversation never ends.

**Default flow consistency:** Every `default_next_phase` target in the orchestrator rules must also appear in that phase's `allowed_targets` in the registry. If the default flow says "after A go to B" but A's registry entry doesn't list B as an allowed target, the transition will be blocked.

**Field coverage in skill files:** Every field in a phase's schema should be mentioned in that phase's analyzer.md. If a field exists in the schema but the analyzer never looks for it, it will never be extracted.

**Ambiguity check:** For enum fields, verify that the analyzer.md includes synonym mappings for common variations. If the schema defines `enum: formal | casual` but the analyzer doesn't map "relaxed" or "professional," extraction will miss valid inputs.

**Entity config consistency:** For entity-bearing phases, every field listed in `per_entity_fields` and `phase_level_fields` in the schema must appear in that phase's analyzer.md. The union of per-entity and phase-level fields must equal the phase's total field set — no field should be missing from both.

**Entity rotation exit conditions:** Every entity-bearing phase must have an exit condition in the orchestrator rules' Entity Rotation Rules section. Without an exit condition, the entity loop runs indefinitely.

**Entity rotation rule field references:** Every field name in the Entity Rotation Rules' rotation trigger must exist in the corresponding phase's `per_entity_fields` in the schema.

### Self-Validation Checklist

Before delivering the generated artifacts, verify:

- Are field names consistent across analyzer.md and speaker.md for the same phase?
- Do all transition targets in analyzer.md files exist in the phase registry?
- Are completion criteria testable and unambiguous?
- Does the state schema include every field referenced in every phase?
- Are there orphaned phases (no transition path leads to them)?
- Do speaker.md files avoid referencing internal field names or phase labels?
- Do entity-bearing phases have `entity_config` in the schema with valid `rotation_rule` and `min/max_entities`?
- Do per-entity and phase-level fields in the schema cover all fields listed in the phase design?
- Do analyzer.md files for entity-bearing phases include entity-switch detection examples (with negatives)?
- Do speaker.md files for entity-bearing phases include entity rotation guidance?
- Is entity-switch detection in analyzer.md files clearly separated from cross-phase detection (no `phase_suggestion` for entity switches)?

For the per-phase skill file checklist (within and across files), see Skill 1 Part 5.

### Configuration Validation Script

Generate `tests/validate_config.ts` — a standalone script that runs all pre-deployment consistency checks from Skill 9 Part 1 without requiring LLM calls or a running application. This script validates the configuration artifacts (JSON, markdown) using the same TypeScript toolchain as the rest of the project.

The script must check:

1. **File completeness** — every phase in the registry has both `skills/{phase}/analyzer.md` and `skills/{phase}/speaker.md`; all three prompt templates exist in `prompts/`; all config files exist.
2. **Registry integrity** — `default_phase` exists, all `allowed_targets` reference existing phases, all targets have conditions, all phases are reachable, at least one terminal condition exists.
3. **Schema consistency** — every phase in the registry has a schema entry (and vice versa), field names match across schema and skill files, types and required/optional flags match.
4. **Prompt template placeholders** — all required `{{placeholder}}` variables are present in each template (see Skill 9 Check 4 for the full list).
5. **Business rule references** — every field and phase referenced in `orchestrator_rules.md` exists in the schema and registry.

Output a pass/fail report. Any failure must be fixed before proceeding to the runtime smoke test.

### Runtime Smoke Test

After configuration validation passes, run a runtime smoke test to verify the agent starts and can process at least one turn without crashing. The runtime smoke test is implementation-specific — it lives in the implementation's test directory (e.g., `src/tests/smoke-test.ts` for a TypeScript implementation), not in `agent_config/`. It initializes the conversation engine with the generated config, triggers the opening message (verifying the Speaker produces a non-empty response), sends a simple user message like "Hello, I need some help," and confirms the engine returns a non-empty response and remains active. If any step fails, there's a structural problem that the configuration checks missed. See the implementation spec for the runtime smoke test structure.

---

## Output: Complete File Structure

After the full generation process, you have:

```
agent_config/
├── state_schema.json           # Stage 5
├── phase_registry.json         # Stage 5
├── orchestrator_rules.md       # Stage 5
├── skills/
│   ├── {phase_one}/            # One folder per phase from the phase design
│   │   ├── analyzer.md         # Stage 6
│   │   └── speaker.md          # Stage 6
│   ├── {phase_two}/
│   │   ├── analyzer.md         # Stage 6
│   │   └── speaker.md          # Stage 6
│   └── {phase_n}/              # Repeat for every phase in the registry
│       ├── analyzer.md         # Stage 6
│       └── speaker.md          # Stage 6
├── prompts/
│   ├── analyzer_template.md    # Stage 5 (from Skill 2 — copied or customized per domain)
│   ├── speaker_template.md     # Stage 5 (from Skill 3 — copied or customized per domain)
│   └── summary_template.md     # Stage 5 (from Skill 7 — copied or customized per domain)
└── tests/
    ├── fixtures/
    │   └── synthetic_conversations.json  # Stage 7
    └── validate_config.ts                # Stage 7 (pre-deployment config validation — no LLM calls)
```

**Note on tests:** The `tests/` directory contains pre-deployment configuration validation — deterministic checks that verify cross-artifact consistency without requiring LLM calls or a running application (see Skill 9 Part 1). `validate_config.ts` checks file completeness, registry integrity, schema consistency, prompt template placeholders, and business rule references. The runtime smoke test (which starts the agent and processes a turn) is implementation-specific and lives in the implementation's own test directory — see the implementation spec for details.

**Note on prompt templates:** The `prompts/` directory contains framework-level templates defined by Skill 2 (Analyzer Prompt Engineering), Skill 3 (Speaker Prompt Engineering), and Skill 7 (Conversation History Management). These provide the default structure and are reusable across agents — most domains use them as-is. However, some domains require customization of the Global Rules, Output Format, or communication behavior sections (see Customization Points in Skills 2, 3, and 7). When customization is needed, it is applied during Stage 5 (Build Config). At runtime, the engine loads a template, injects domain-specific content into it via `{{placeholders}}`, and sends the assembled prompt to the LLM. See Skills 2, 3, and 7 for the full template definitions and placeholder contracts.

---

## Generation Checklist

Use this checklist after generating all artifacts:

```
□ Plan & Confirmation
  □ Plan presented with phase overview, transition map, assumptions
  □ Ambiguous decisions surfaced as concrete choices
  □ User confirmed or feedback incorporated

□ Requirements Analysis
  □ All data points identified
  □ Dependencies mapped
  □ Workflow shape determined

□ Phase Design
  □ Phases align with natural conversation segments
  □ No phase has more than 6 required fields
  □ No phase has fewer than 2 fields (merge if so)
  □ Phase names are descriptive snake_case

□ State Schema
  □ Every collected field has a schema entry
  □ Types are correct (especially enums)
  □ Required/optional correctly assigned
  □ Update policies match domain needs
  □ Display names are natural language

□ Phase Registry
  □ Default phase is set correctly
  □ All transition targets exist
  □ Conditions are defined for all transitions
  □ Max turns set per phase
  □ All phases reachable from default
  □ At least one terminal condition exists

□ Orchestrator Rules
  □ default_next_phase defined for all non-terminal phases
  □ cross_phase_context configured for phases that need prior context
  □ Business rules encode domain constraints
  □ No model names, API keys, or token budgets in this file

□ Phase Skills
  □ analyzer.md and speaker.md exist for every phase
  □ Follow Skill 1 templates and pass Skill 1's consistency checklist
  □ Field names exactly match state schema
  □ Transition targets exist in phase registry
  □ No duplication of global rules already in Skill 2/3 templates

□ Entity Structure
  □ Entity-bearing phases have entity_config in schema (Skill 4)
  □ per_entity_fields + phase_level_fields = all phase fields
  □ min_entities and max_entities set with exit conditions
  □ rotation_rule defined and referenced in orchestrator rules
  □ analyzer.md includes entity-switch detection examples (with negatives)
  □ speaker.md includes entity rotation flow guidance
  □ Entity-switch detection does NOT use phase_suggestion

□ Prompt Templates
  □ prompts/analyzer_template.md present (from Skill 2, copied or customized in Stage 5)
  □ prompts/speaker_template.md present (from Skill 3, copied or customized in Stage 5)
  □ prompts/summary_template.md present (from Skill 7, copied or customized in Stage 5)
  □ Any domain customizations to templates are documented and justified
  □ Placeholder names in templates match what prompt-loader.ts provides

□ Validation
  □ Cross-artifact consistency check passes (Stage 7 validator)
  □ Self-validation checklist passes
  □ Configuration validation script passes (validate_config.ts — no LLM calls)
  □ Runtime smoke test passes (implementation-specific — see implementation spec)

□ Review
  □ Domain expert reviewed phase skills
  □ Tone matches target audience
  □ Edge cases reflect real user behavior
```

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Jumping straight to artifacts without a plan | Rework when user disagrees with structure | Always run Stages 1–2 first; confirm before generating |
| Asking abstract questions instead of proposing | User can't give useful feedback | Generate a concrete plan, surface decisions as choices |
| Too many phases | Transitions feel abrupt, conversation fragmented | Merge phases that collect fewer than 3 fields |
| Too few phases | Single phase collects 10+ fields, feels like interrogation | Split into natural conversation stages |
| Field names that are too technical | Leak into Speaker output, confusing to users | Use display_name for Speaker; keep field names for internal use |
| Missing cross-phase context config | Speaker in phase B has no context from phase A | Configure cross_phase_context for every phase that needs prior context |
| Business rules missing | Agent allows invalid states (e.g., system design for juniors) | Define business rules in orchestrator_rules.md for every domain constraint |
| Enum values don't match user vocabulary | Extraction fails on valid inputs like "sys design" | Add common variations as examples in analyzer.md |
| No terminal phase | Conversation never ends | Ensure at least one phase has empty allowed_targets or a conditional exit |
| Schema fields without display_name | Speaker has to use field names | Add display_name to every field in the schema |
| Optional fields treated as required in skills | User can never "finish" a phase | Clearly mark optional fields in analyzer.md; speaker.md should not aggressively pursue them |
| Phase skills duplicate global rules from templates | Token waste, risk of conflicting instructions | Check Skills 2/3 to see what the framework template already provides; only add phase-specific rules |
| Model names or API keys in orchestrator_rules.md | Breaks when deploying to a different provider or environment | Model names go in implementation config; API keys go in .env; orchestrator rules contain only behavioral parameters |
| Using entity structure when a `string[]` field suffices | Unnecessary complexity, extra LLM calls for entity rotation | Only use entities when instances have 2+ internal fields |
| Missing entity exit condition | Entity loop never ends, phase never completes | Define explicit exit in orchestrator rules Entity Rotation Rules |
| Per-entity field listed as phase-level (or vice versa) | Field gets overwritten on entity rotation, or persists when it shouldn't | Verify each field's scope matches how users provide the data |
| Entity-switch detection uses `phase_suggestion` | Triggers phase redirect loop instead of entity rotation | Entity switches stay in the same phase — State Updater handles rotation |
| Entity-switch detection examples missing negative cases | Analyzer falsely detects new entity on every mention of related concepts | Include "this is NOT a new entity" examples |

For skill-file-level writing mistakes (vague instructions, missing examples, weak tone guidance, etc.), see Skill 1 Part 4.
