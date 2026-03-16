# Skill 1: Phase Skill Authoring

## Purpose

This skill is the canonical reference for writing `analyzer.md` and `speaker.md` files. Every phase in a multi-phase agent requires exactly these two files — one for extraction, one for communication. This document defines the templates, craft principles, and quality bar for both.

The domain customization process decides *which fields go in which phase*. This skill defines *how to write the instructions for those fields well*.

At runtime, phase skill files don't operate alone — they are injected into framework prompt templates (`prompts/analyzer_template.md` and `prompts/speaker_template.md`). This means the framework templates already provide certain global rules (like "extract only what's explicit" and "never mention field names"). Phase skill files should add phase-specific detail on top, not repeat what the templates already cover. Where this matters, the templates below call it out.

---

## Core Principles

1. **One phase, one responsibility.** Each phase collects a bounded set of information. If a phase is doing too many things, split it.
2. **Required means required.** If a field is marked required, the phase cannot complete without it. Be deliberate about what's truly required.
3. **The Analyzer extracts. The Speaker communicates.** Never mix concerns. No tone guidance in analyzer.md. No extraction rules in speaker.md.
4. **Explicit over implicit.** Tell the AI exactly how to handle ambiguity, partial answers, and edge cases. Vague instructions produce vague results.
5. **Field names are contracts.** Field names in analyzer.md become keys in state. They must match exactly across analyzer.md, speaker.md, the state schema, and orchestrator rules. Use `snake_case`, be descriptive, never rename without updating all references.

---

## Part 1: Analyzer Template

This is the canonical template. Every `analyzer.md` file must follow this structure.

```markdown
# Phase: [phase_name] — Analyzer Instructions

## Objective
[One to two sentences: what this phase is trying to learn from the user.]

## Fields to Extract

### [field_name] (required)
- **What to look for:** [Plain-language description of what the user might say]
- **Type:** [string | integer | boolean | enum: val1 | val2 | string[]]
- **Interpretation:** [Mappings, synonyms, normalization rules]
- **Validation:** [What makes a value valid vs. invalid]
- **Examples:**
  - User says: "[input]" → Extract: "[value]"
  - User says: "[ambiguous input]" → Extract: "[value]", confidence: [level]
  - User says: "[tricky input]" → Do NOT extract. [reason]
- **Do NOT extract if:** [Conditions where extraction would be wrong]

### [field_name] (optional)
- **What to look for:** [description]
- **Type:** [type]
- **Examples:**
  - User says: "[input]" → Extract: "[value]"
- **Do NOT extract if:** [conditions]
- Extract only if explicitly stated. Do not probe or infer.

[Repeat for each field]

## Cross-Phase Detection
If the user mentions a topic that belongs to another phase, flag it:
- If the user mentions [topic from another phase], set `phase_suggestion` to "[target_phase]"
- Examples:
  - "[example]" → phase_suggestion: "[target]"

Do NOT suggest a transition if required fields are still missing — unless the user explicitly refuses to provide them.

## Edge Cases
The following are common defaults. The analyzer framework template
(`prompts/analyzer_template.md`) already provides the global extraction rules
(extract only explicit info, handle corrections, return empty on irrelevant
input). Include these in your phase skill only if the phase needs
domain-specific handling that overrides or extends the defaults:
- [Domain-specific edge cases, e.g.: "If the user mentions a technology
  without being asked, extract it as recruiter_topics"]

## Completion
- Set `required_complete: true` ONLY when ALL of these have non-null values: [list every required field by name]
- Optional fields do NOT affect completion.
- Do NOT set it based on judgment — only based on whether every required field has a value.
```

**Notes on the template:**

- **Output format** is not included here. The JSON structure (`extracted_fields`, `required_complete`, `phase_suggestion`, `confidence`, `notes`) is defined by the analyzer framework template (`prompts/analyzer_template.md`) and injected at runtime. Phase skills should not restate it.
- **Global extraction rules** ("extract only what's explicit," "do not infer," "return empty on irrelevant messages," "extract corrections") are provided by the analyzer framework template. Phase skills should not repeat these — they should add phase-specific extraction guidance (field definitions, examples, "Do NOT extract if" rules) on top.
- **Update policies** (overwrite, append, conflict) are defined in the state schema and enforced by the Orchestrator. You don't need to declare them per field in analyzer.md — the schema is the source of truth.
- **Types** should match the state schema exactly. The standard types are: `string`, `integer`, `boolean`, `string[]`, and `enum: val1 | val2 | val3`.

---

## Part 2: Speaker Template

This is the canonical template. Every `speaker.md` file must follow this structure.

```markdown
# Phase: [phase_name] — Speaker Instructions

## Role
[One sentence: who the Speaker is in this phase.]

## Tone
- [Specific tone guidance with concrete phrasing examples]
- Avoid: [phrases, patterns, or approaches to avoid]

## Opening Message
[Guidance for the first message when this phase begins. On the first turn there is no user message — the Speaker uses this guidance to generate the conversation opener.]

Example opening:
> "[A sample opening showing the right tone and approach.]"

Do NOT: [what to avoid in the opening]

## Questioning Strategy
- Ask for [most important field] first
- Then [next field]
- Group [related fields] into a single natural question when possible
- Never ask for more than [N] things at once
- Prioritize required fields. Only ask for optional fields if the conversation flows there naturally.
- [Domain-specific ordering and grouping guidance]

## Acknowledging Information
The speaker framework template (`prompts/speaker_template.md`) already
instructs the Speaker to acknowledge user input and summarize naturally.
Use this section for phase-specific guidance on *how* to acknowledge
in this domain:
- Use their specific details ("Google," not "the company").
- Keep acknowledgments brief — one sentence, not a paragraph.
- If the user provided multiple pieces, acknowledge the key ones, don't parrot everything back.
- [Domain-specific acknowledgment style, e.g.: "Add a touch of personality
  or relevant context when natural"]

## When Everything Is Collected
[What to say when all required fields are complete.]
- Briefly summarize the highlights naturally — do not list every field.
- Signal readiness to move forward without naming the next phase.

## Edge Cases
The speaker framework template (`prompts/speaker_template.md`) handles
generic situations (user asks a question, user goes off-topic). Use this
section for phase-specific edge cases that need domain-aware handling:
- **User provides info for a different phase:** [How to redirect in this phase's tone]
- **User is vague or uncertain:** [Domain-specific options or examples to offer]
- **User refuses to answer:** Respect it. If the field is required, gently explain why it helps (once). Do not ask more than twice.
- [Other domain-specific edge cases]

## Things to NEVER Do
The speaker framework template (`prompts/speaker_template.md`) already
prohibits: mentioning field names, phase names, or system internals;
saying "required" or "optional"; asking for already-collected information;
including JSON or metadata; and deciding phase transitions. You do not
need to repeat these in every phase skill.

Use this section only for **domain-specific prohibitions** — things the
framework template can't know about:
- [e.g.: "Never give interview advice during the setup phase — save it for later"]
- [e.g.: "Never ask 'What is your seniority level?' — too stiff. Say 'What level is the role?'"]
- [e.g.: "Never list bullet points of what you still need — conversational flow only"]
```

---

## Part 3: Writing Well — Craft Guidance

The templates define structure. This section defines quality. The difference between a mediocre phase skill and a good one is almost always in the specificity of the instructions.

### Analyzer: Be specific about mappings

```
BAD:
- role_level: The seniority of the role.

GOOD:
### role_level (required)
- **What to look for:** The seniority level of the target role.
- **Type:** enum: junior | mid | senior | staff
- **Interpretation:** Map common synonyms:
    - "entry-level", "new grad", "junior" → junior
    - "mid-level", "intermediate" → mid
    - "senior", "experienced", "lead" → senior
    - "staff", "staff-level" → staff
  If the user gives years of experience without a level,
  do not infer. Leave unset.
```

### Analyzer: Be specific about boundaries

```
BAD:
- timeline: When the interview is.

GOOD:
### interview_timeline (optional)
- **What to look for:** When the user expects the interview to occur.
- **Type:** string
- Accept relative dates ("next week") and specific dates ("March 15th").
  Do not convert relative to absolute — store as stated.
- **Do NOT extract if:** The user says "soon" or "eventually" — too vague.
```

### Analyzer: Be specific about what NOT to do

```
BAD:
- technical_areas: Technical topics for the interview.

GOOD:
### technical_areas (optional)
- **What to look for:** Specific technical domains the user explicitly mentions.
- **Type:** string[]
- Extract only topics the user states directly.
- Do NOT infer topics from company or role.
- Do NOT expand abbreviations into extra topics
  ("ML" → "machine learning" is fine, but don't add
  "deep learning" as a bonus entry).
```

### Speaker: Demonstrate tone, don't just declare it

```
BAD:
## Tone
- Be friendly

GOOD:
## Tone
- Warm and supportive, like a knowledgeable friend — not a
  formal counselor or a chatbot.
- Use conversational language: "Got it!" not "Acknowledged."
- Match the user's energy. Excited → reflect it. Nervous → reassure.
- Avoid: corporate jargon ("let's align"), excessive enthusiasm
  ("That's AMAZING!"), robotic transitions ("Moving on to the
  next question...").
```

### Speaker: Make questions feel natural, not like form fields

```
BAD:
- interview_format: "What is your interview format?"

GOOD:
- interview_format: "Do you know what the interview will look like —
  phone screen, system design round, coding session, or a full
  onsite loop?"
  - If partially provided ("technical interview"): "When you say
    technical, do you mean coding, system design, or a mix?"
```

### Speaker: Opening messages should create momentum

```
BAD:
## Opening Message
"Hello! I'll be collecting some information from you."

GOOD:
## Opening Message
Greet the user, briefly explain what this step covers, and ask the
first (easiest) required question.

Example:
> "Hey! Let's get your mock interview set up. First off — which
> company are you interviewing with?"

Do NOT: list everything you'll be asking about.
```

---

## Part 4: Common Mistakes

### Analyzer Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No examples for ambiguous inputs | AI guesses inconsistently | Add 2–3 examples showing edge cases |
| Vague types like "info about the role" | Unstructured extraction | Break into specific typed fields |
| No "Do NOT extract" rules | Hallucinated values | Add explicit exclusion conditions per field |
| No edge case handling | Breaks on unusual input | Cover corrections, multi-field messages, off-topic input |
| Mixing in tone or communication guidance | Analyzer tries to craft responses | Keep extraction rules only |
| Missing completion criteria | Phase never finishes or finishes too early | List every required field by name in the Completion section |

### Speaker Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No opening message guidance | First turn is awkward or generic | Add opening section with example |
| Field names used as questions | Feels like a form | Write natural-language questions with examples |
| No acknowledgment guidance | Agent ignores what user said, just asks the next thing | Add acknowledgment section with good/bad examples |
| Tone described but not demonstrated | AI interprets "friendly" unpredictably | Give concrete phrasing examples |
| No phase completion guidance | Agent doesn't know how to wrap up | Add completion section with transition phrasing |
| No edge cases | Agent freezes on unexpected input | Cover refusals, tangents, vagueness, questions |

---

## Part 5: Consistency Checklist

Run this before finalizing any phase's skill files.

### Within the phase:
- [ ] Every field in analyzer.md has a corresponding question approach in speaker.md
- [ ] Every field in analyzer.md has a declared type
- [ ] Field names are identical in both files (exact `snake_case` match)
- [ ] analyzer.md has at least one extraction example per required field
- [ ] analyzer.md has a "Do NOT extract" rule for every field prone to ambiguity
- [ ] analyzer.md lists every required field by name in the Completion section
- [ ] speaker.md has an opening message section with an example
- [ ] speaker.md has a phase completion section
- [ ] Neither file references concerns that belong to the other

### Across phases:
- [ ] No two phases collect the same field (if shared, one phase owns it)
- [ ] Transition targets in analyzer.md exist in the phase registry
- [ ] Phase ordering makes conversational sense — phase B's opening flows from phase A's completion

### Against the state schema:
- [ ] Every field name in analyzer.md exists in the state schema
- [ ] Field types match between analyzer.md and the state schema
- [ ] Required/optional flags match between analyzer.md and the state schema

For the full cross-artifact validation (schema ↔ registry ↔ rules ↔ skills), see the domain customization validation stage.
