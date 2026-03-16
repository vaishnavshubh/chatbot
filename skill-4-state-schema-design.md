# Skill 4: State Schema Design

## Purpose

This skill is the canonical reference for writing `state_schema.json` — the configuration file that defines every field the agent collects, organized by phase. The state schema is the contract between components: the Analyzer extracts values into these fields, the State Updater validates and merges against them, and the Speaker reads from them.

The state schema works alongside two other configuration artifacts:

- `phase_registry.json` — defines phase names, transitions, and turn limits
- `orchestrator_rules.md` — defines business rules, cross-phase context, and operational config

The domain customization process decides *which phases exist and what they collect*. This skill defines *how to design fields that are unambiguous, correctly typed, and behave well at runtime*.

---

## Core Principles

1. **Every field has one owner.** A field belongs to exactly one phase. If two phases need the same information, one phase collects it and the other reads it via cross-phase context.
2. **Null means "not yet collected."** Every field starts as null (or an empty array for append fields). The State Updater uses null to distinguish "we haven't asked yet" from "the user said zero" or "the user said no."
3. **Derived values are computed, not stored.** Things like "what fields are missing" or "is this phase complete" are computed from the schema on demand, not stored as separate fields that can drift out of sync.
4. **Field names are contracts.** A field name in the schema must match exactly in the phase's analyzer.md, speaker.md, orchestrator_rules.md, and phase_registry.json. Use `snake_case`, be descriptive, never rename without updating all references.
5. **The schema describes data, not behavior.** What to extract, how to ask, when to transition — those belong in phase skills and orchestrator rules. The schema only declares what fields exist, what type they are, and how they update.

---

## Template

Every `state_schema.json` file follows this structure:

```json
{
  "version": "1.0",
  "phases": {
    "{phase_name}": {
      "{field_name}": {
        "type": "string",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Human-Readable Label",
        "description": "What this field captures, in plain language."
      }
    }
  }
}
```

Each phase is a key. Each field within a phase is a nested object with the properties described below.

The template above applies to standard flat phases. For entity-bearing phases — phases that collect the same set of fields for multiple instances (e.g., multiple projects, symptoms, or products) — see the Entity-Bearing Phases section below for the extended format with `entity_config`, `per_entity_fields`, and `phase_level_fields`. Non-entity phases are completely unaffected by this extension.

---

## Field Properties

### type

The data type of the field. Must match the type declared in the phase's analyzer.md.

| Type | Use for | Example value |
|------|---------|---------------|
| `string` | Free-text values | `"Google"` |
| `integer` | Whole numbers | `3` |
| `boolean` | Yes/no flags | `true` |
| `enum: val1 \| val2 \| val3` | Constrained choices | `"senior"` |
| `string[]` | Lists of text values | `["distributed systems", "databases"]` |
| `object[]` | Lists of structured items | `[{"question": "...", "answer": "..."}]` |

Use the most specific type possible. If a field has a fixed set of valid values, use `enum` — don't use `string` and hope the Analyzer guesses correctly.

### required

Whether the phase can complete without this field. `true` means the State Updater will not mark the phase complete until this field is non-null. `false` means the field is collected opportunistically.

Be deliberate. Every required field is a question the user *must* answer before the conversation can advance. Too many required fields make the conversation feel like an interrogation. Too few means the agent advances without enough information to be useful.

### update_policy

How the State Updater handles a new value when the field already has one.

**overwrite** — Replace the old value with the new one. Use for fields where the user might correct themselves ("Actually, it's mid-level, not senior"). Most fields use overwrite.

**append** — Merge the new value into the existing array. Deduplicate exact matches. Use for list fields where values accumulate over the conversation ("I also want to cover databases" adds to the existing technical_areas list).

**conflict** — Do not update. Keep the existing value and flag the field for clarification. Use for fields where a second, different value is ambiguous rather than a correction (e.g., the user mentions both Google and Amazon without indicating which one they mean for this session). The Speaker will ask the user to clarify.

When choosing a policy, ask: "If the user says something different for this field, are they correcting themselves (overwrite), adding to a list (append), or is it genuinely ambiguous (conflict)?"

### default

The initial value when the conversation starts. Almost always `null`, meaning "not yet collected."

Exceptions:
- `string[]` and `object[]` fields: use `[]` (empty array) so append operations work without null checks.
- Counter fields that have a meaningful zero: still use `null` as default, and set to `0` explicitly when the first value is collected. This prevents the State Updater from confusing "not yet counted" with "count is zero."

Never use `0` or `false` as defaults for fields where those are meaningful collected values. The State Updater uses null to determine what's missing.

### display_name

A short, human-readable label for the field. Used when the Speaker Prompt Creator assembles cross-phase context and collected-data summaries for the Speaker, so the Speaker never sees raw field names.

```
BAD:
"display_name": "target_company"

GOOD:
"display_name": "Company"
```

Every field must have a display_name. If you skip it, the Speaker Prompt Creator falls back to converting the field name (e.g., `target_company` → "Target Company"), which usually reads awkwardly.

### description

A plain-language explanation of what the field captures. Used when formatting missing-field lists for the Speaker (so it knows what to ask about without seeing field names) and for documentation.

```
BAD:
"description": "target_company"

GOOD:
"description": "The company where the user is interviewing."
```

Write it as a sentence fragment that completes "This field captures..." or could be shown to a user as a question topic.

---

## Craft Guidance

### Use enum over string when values are constrained

If there are fewer than ~10 valid values and they're known in advance, use enum. This gives the Analyzer a closed set to map to and prevents drift.

```
BAD:
"role_level": {
  "type": "string",
  ...
}

GOOD:
"role_level": {
  "type": "enum: junior | mid | senior | staff | principal",
  ...
}
```

The Analyzer's phase skill (analyzer.md) should list synonyms and mappings for each enum value. The schema declares the valid values; the phase skill teaches the Analyzer how to map user language to those values.

### Group related information into one field or split into distinct fields — don't do both

If "interview format" is a single concept (phone screen, coding, system design), make it one enum field. Don't also create a separate `is_system_design` boolean. Redundant fields drift out of sync.

If "technical areas" is genuinely a list of independent items, make it a `string[]`. Don't create separate `technical_area_1`, `technical_area_2` fields — that limits the list artificially.

### Keep field counts reasonable per phase

A phase with 3–6 fields feels like a natural conversation. A phase with 12+ fields feels like a form. If a phase has too many fields, consider splitting it into two phases or making some fields optional.

Required fields especially should be kept to a minimum — 2–4 per phase is typical. Each required field is a question the user cannot skip.

### Match field granularity to how users talk

Design fields around how users naturally express information, not around how you'd model it in a database.

```
BAD — too granular:
"interview_month": { "type": "string" },
"interview_day": { "type": "integer" },
"interview_year": { "type": "integer" }

GOOD — matches natural expression:
"interview_timeline": { "type": "string" }
```

Users say "next week" or "March 15th" — they don't decompose dates into separate components. Store it as they say it.

### Don't duplicate fields across phases

If both "question practice" and "session feedback" need to know the company, the company field lives in "interview setup" (the phase that collects it). The other phases access it through cross-phase context configured in `orchestrator_rules.md`.

If you find yourself wanting the same field in two phases, that's a signal to use cross-phase context instead.

### Don't force entity structure onto simple lists

If the user provides a list of items without internal structure — skills, interests, preferences — use a `string[]` field with `append` policy. Entity structure is for instances with 2+ internal fields that are discussed one at a time.

```
BAD — over-engineered:
"entity_config": { "entity_name": "skill" }
"per_entity_fields": { "skill_name": { "type": "string" } }

GOOD — simple list:
"technical_skills": {
  "type": "string[]",
  "update_policy": "append",
  ...
}
```

### Keep per-entity field counts small

Each entity instance is a mini-conversation. If an entity has 6+ per-entity fields, the conversation within each entity will feel like an interrogation. 2–4 per-entity required fields is typical.

### Phase-level fields should be rare

Most fields in an entity-bearing phase are per-entity. Phase-level fields exist for information that genuinely spans all entities (e.g., "overall theme across all projects"). If most fields are phase-level, the phase probably shouldn't use entity structure.

---

## Example: Mock Interview Agent

```json
{
  "version": "1.0",
  "phases": {
    "interview_setup": {
      "target_company": {
        "type": "string",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Company",
        "description": "The company where the user is interviewing."
      },
      "role_title": {
        "type": "string",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Role",
        "description": "The specific job title for the role."
      },
      "role_level": {
        "type": "enum: junior | mid | senior | staff | principal",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Level",
        "description": "The seniority level of the role."
      },
      "interview_format": {
        "type": "enum: phone_screen | coding | system_design | behavioral | onsite_loop | unknown",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Interview format",
        "description": "The format of the interview."
      },
      "interview_timeline": {
        "type": "string",
        "required": false,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Timeline",
        "description": "When the interview is scheduled."
      },
      "technical_areas": {
        "type": "string[]",
        "required": false,
        "update_policy": "append",
        "default": [],
        "display_name": "Technical focus areas",
        "description": "Specific technical topics expected in the interview."
      },
      "preparation_level": {
        "type": "enum: none | some | significant",
        "required": false,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Preparation level",
        "description": "How much the user has already prepared."
      }
    },
    "question_practice": {
      "questions_completed": {
        "type": "integer",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Questions completed",
        "description": "Number of practice questions completed this session."
      },
      "user_responses": {
        "type": "object[]",
        "required": true,
        "update_policy": "append",
        "default": [],
        "display_name": "Responses",
        "description": "The user's answers to practice questions."
      },
      "topic_focus": {
        "type": "string",
        "required": false,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Topic focus",
        "description": "Specific topic the user wants to focus on."
      }
    },
    "session_feedback": {
      "feedback_acknowledged": {
        "type": "boolean",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Feedback acknowledged",
        "description": "Whether the user has acknowledged the session feedback."
      },
      "wants_more_practice": {
        "type": "boolean",
        "required": true,
        "update_policy": "overwrite",
        "default": null,
        "display_name": "Wants more practice",
        "description": "Whether the user wants another round of practice."
      }
    }
  }
}
```

Things to notice in this example:

- **4 required fields in setup, 2 in practice, 2 in feedback.** Each phase has a manageable ask.
- **`questions_completed` defaults to null, not 0.** Zero is a meaningful value (the user hasn't done any yet). Null means "we haven't started tracking yet."
- **`technical_areas` uses append.** The user might mention topics across multiple messages.
- **`target_company` uses overwrite, not conflict.** If the user says a different company, they're correcting — not being ambiguous. Conflict would be appropriate if the user said "I'm interviewing at both Google and Amazon" without clarifying which one this session is for.
- **`feedback_acknowledged` defaults to null, not false.** False would mean "asked and said no." Null means "hasn't been asked yet."
- **Every field has display_name and description.** The Speaker never sees `target_company` — it sees "Company."

---

## Entity-Bearing Phases

Some phases collect the same set of fields multiple times for different instances — multiple work projects, multiple symptoms, multiple products. These are entity-bearing phases.

### When to Use Entities

Use entity structure when:
- The same set of 2+ fields is collected for multiple instances
- Users naturally provide these instances one at a time in conversation
- The agent needs to steer between instances ("Tell me about your next project")

Do NOT use entity structure when:
- A simple `string[]` append field captures what's needed (e.g., a list of skills)
- The "instances" don't have internal structure (just names or labels)
- There's always exactly one instance

### Schema Format

Entity-bearing phases replace the flat field list with three sections:

```json
{
  "version": "1.0",
  "phases": {
    "experience_review": {
      "entity_config": {
        "entity_name": "project",
        "display_name": "Work Project",
        "min_entities": 1,
        "max_entities": 5,
        "rotation_rule": "after_core_questions_answered"
      },
      "per_entity_fields": {
        "project_name": {
          "type": "string",
          "required": true,
          "update_policy": "overwrite",
          "default": null,
          "display_name": "Project Name",
          "description": "The name or title of the work project."
        },
        "project_role": {
          "type": "string",
          "required": true,
          "update_policy": "overwrite",
          "default": null,
          "display_name": "Your Role",
          "description": "The user's role on this project."
        },
        "technologies": {
          "type": "string[]",
          "required": false,
          "update_policy": "append",
          "default": [],
          "display_name": "Technologies Used",
          "description": "Technical tools and frameworks used on this project."
        }
      },
      "phase_level_fields": {
        "overall_experience_theme": {
          "type": "string",
          "required": false,
          "update_policy": "overwrite",
          "default": null,
          "display_name": "Experience Theme",
          "description": "Common thread or pattern across the user's projects."
        }
      }
    }
  }
}
```

### entity_config Properties

| Property | Type | Description |
|----------|------|-------------|
| `entity_name` | string | Singular noun for what one entity is (e.g., "project", "symptom", "product"). Used internally. |
| `display_name` | string | Human-readable label the Speaker uses (e.g., "Work Project"). |
| `min_entities` | integer | Minimum entities required before the phase can complete. |
| `max_entities` | integer or null | Maximum entities. Null if unbounded (but rotation rules must have an exit condition). |
| `rotation_rule` | string | When to advance to the next entity. Defined in orchestrator_rules.md Entity Rotation Rules section. |

### How Entity Fields Behave

- **Per-entity fields** follow all the same property rules as flat fields (type, required, update_policy, default, display_name, description). They apply independently to each entity instance.
- **Phase-level fields** are collected once for the whole phase and persist across entity rotations. They follow the same rules as flat-phase fields.
- **Per-entity required fields** must all be non-null for the current entity before entity rotation can occur. Phase completion requires `min_entities` met with all per-entity required fields filled, plus all phase-level required fields filled.
- **Per-entity defaults** apply fresh for each new entity. When rotating to entity N+1, per-entity fields initialize to their defaults (null or [] for arrays).
- **The union of per_entity_fields and phase_level_fields must equal the phase's total field set.** No field should appear in both, and no field should be missing from both.

### Core Principles Still Apply

All existing principles hold for entity-bearing phases:
- Every field has one owner (the phase). Per-entity fields are not shared between entities — each entity has its own instance.
- Null means "not yet collected" — for each entity instance independently.
- Field names are contracts — per-entity field names must match across schema, analyzer.md, and speaker.md just like flat fields.
- The schema describes data, not behavior — rotation rules and exit conditions belong in orchestrator_rules.md, not in the schema.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using `0` or `false` as default for fields where those are meaningful | State Updater can't tell "not collected" from "collected as zero/false" | Use `null` as default; set `0` or `false` explicitly when collected |
| Missing display_name | Speaker sees raw field names like `target_company` or awkward auto-conversions | Add a short, natural display_name to every field |
| Missing description | Speaker doesn't know what to ask about when listing missing fields | Add a plain-language description to every field |
| Field name collision across phases | Ambiguous state, merge conflicts | Each field belongs to exactly one phase; use cross-phase context for sharing |
| Using `string` when `enum` is appropriate | Analyzer extracts inconsistent values ("sr", "Senior", "senior-level") | Use enum with a closed set; teach mappings in analyzer.md |
| Too many required fields | Conversation feels like an interrogation | Keep required fields to 2–4 per phase; make the rest optional |
| Storing derived values as fields | Values drift out of sync with source data | Compute derived values (missing fields, completion status) on demand |
| No update_policy specified | State Updater doesn't know whether to overwrite, append, or flag conflicts | Every field must declare an update_policy |
| Redundant fields across phases | Same data in two places, one gets stale | One phase owns the field; others read via cross-phase context |
| Overly granular fields that don't match how users talk | Extraction fails or feels unnatural ("What month is your interview?") | Design fields around natural user expression |
| Using entity structure when a `string[]` field suffices | Unnecessary complexity, extra LLM calls for entity rotation | Only use entities when instances have 2+ internal fields |
| Per-entity field listed as phase-level (or vice versa) | Field gets overwritten on entity rotation, or persists when it shouldn't | Verify each field's scope matches how users naturally provide the data |
| Missing `entity_config` on an entity-bearing phase | State Updater doesn't know about entity rotation, treats fields as flat | Always include `entity_config` when using `per_entity_fields` |
| `max_entities` is null with no exit condition in orchestrator rules | Entity loop runs indefinitely | Either set `max_entities` or ensure orchestrator rules define an explicit exit |
| Same field name in both `per_entity_fields` and `phase_level_fields` | Ambiguous merge target — State Updater doesn't know where to put extracted values | Each field must appear in exactly one section |

---

## Consistency Checklist

Run this before finalizing `state_schema.json`.

### Against phase skill files (analyzer.md):
- [ ] Every field in every phase's analyzer.md has a corresponding entry in the schema
- [ ] Field names match exactly (same `snake_case`)
- [ ] Field types match exactly
- [ ] Required/optional flags match
- [ ] Enum values in the schema match the enum values in analyzer.md

### Against phase skill files (speaker.md):
- [ ] Every field has a display_name that reads naturally in conversation
- [ ] Every field has a description the Speaker can use to formulate questions

### Against phase_registry.json:
- [ ] Every phase in the registry has a corresponding section in the schema
- [ ] No phases in the schema that don't exist in the registry

### Against orchestrator_rules.md:
- [ ] Every field referenced in cross-phase context rules exists in the schema
- [ ] Every field referenced in business rules exists in the schema
- [ ] Field names in rules match the schema exactly

### Internal consistency:
- [ ] No field name appears in more than one phase
- [ ] All defaults are `null` (or `[]` for array fields) — not `0` or `false` for fields where those are meaningful values
- [ ] Every field has type, required, update_policy, default, display_name, and description

### Entity-bearing phases:
- [ ] Every entity-bearing phase has `entity_config` with all required properties (entity_name, display_name, min_entities, max_entities, rotation_rule)
- [ ] `per_entity_fields` and `phase_level_fields` are mutually exclusive (no field in both)
- [ ] Union of per_entity_fields + phase_level_fields = all fields for the phase
- [ ] `min_entities` is at least 1
- [ ] `max_entities` is set, or orchestrator_rules.md defines an explicit exit condition
- [ ] `rotation_rule` matches a rule defined in orchestrator_rules.md Entity Rotation Rules
- [ ] `display_name` on entity_config reads naturally ("Work Project", not "project_entity")
- [ ] Per-entity required field count is 2–4 (not excessive)
