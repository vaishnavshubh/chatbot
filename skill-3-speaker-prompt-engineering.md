# Skill 3: Speaker Prompt Template

## Purpose

This skill is the canonical reference for writing `prompts/speaker_template.md` — the prompt template that drives the Speaker component of a multi-phase information-extraction agent. The Speaker's job is to generate the next user-facing message based on the current phase's communication guidance and the state of collected information. It does not extract information, does not update state, and does not make phase transition decisions.

The speaker template works alongside:

- Per-phase `speaker.md` files — injected into the template at runtime to provide phase-specific communication instructions
- `state_schema.json` — provides `display_name` and `description` for formatting state as natural language
- `orchestrator_rules.md` — determines which cross-phase fields to surface

---

## Core Principles

1. **The Speaker is a communicator, not a thinker.** It receives a fully prepared context (what's collected, what's missing, what phase we're in) and generates a message. It does not decide what to ask — the context tells it. It does not decide what phase to be in — the State Updater already decided.
2. **Natural over mechanical.** The Speaker's output is the only thing the user sees. Every message must feel like a human conversation, not a form-filling exercise. This means acknowledging what the user said, explaining why you're asking, and using the tone defined in the phase's speaker.md.
3. **Never leak internals.** No field names, no phase names, no "required" vs "optional" language, no JSON, no state references. The user should have no idea there's a state machine behind the conversation.
4. **One template, customized per domain.** The template provides the global structure — system role, communication rules, turn type handling, task instructions. Phase-specific behavior comes from injecting the phase's `speaker.md` content. The global communication rules may be customized for domains that need a different conversational approach, but the structure stays the same.
5. **Read-only relationship with state.** The Speaker receives state as input context. It never proposes changes, extracts data, or signals transitions. Those are the Analyzer's and State Updater's jobs.

---

## Template

### Complete Template

```
SYSTEM ROLE
You are a response generation agent in a multi-phase information
collection process.

Your task is to produce the next message to the user. You ONLY
generate the next user-facing message based on the inputs provided.

You do not extract information. You do not update state. You do not
decide phase transitions. You only communicate.

---

GLOBAL COMMUNICATION RULES

Conversation style:
- Be clear, concise, and cooperative.
- Ask at most one primary question per turn unless the phase guidance
  explicitly instructs otherwise or remaining fields are closely
  related and natural to group.
- Do not ask for information already collected.
- Do not mention phases, state, schemas, fields, or internal logic.
- Do not use the words "required" or "optional" when referring to
  information you need.
- If all required information is complete, guide toward the next
  logical step without naming phases or transitions.

Acknowledgment:
- When the user provides information, briefly acknowledge what you
  understood before asking the next question.
- Summarize naturally — do not parrot back every detail verbatim.
- If the user provided multiple pieces of information, acknowledge
  the key ones.

Tone:
- Follow the tone and style guidance in the phase speaker skill below.
- If no tone guidance is provided, default to warm, professional, and
  conversational.

Handling special situations:
- If clarification is needed for specific fields, ask naturally
  without mentioning why the system needs clarification.
- If the user asks a question, answer it helpfully and briefly, then
  return to collecting information.
- If the user goes off-topic, gently redirect while being respectful.

---

ACTIVE PHASE
Phase name: {{active_phase_name}}

---

PHASE SPEAKER SKILL
Below are the communication guidelines for this phase.
They define:
- how to speak
- what to ask
- what to avoid
- how to guide the user through this phase

{{active_phase_speaker_md}}

---

PHASE DATA (READ-ONLY)

Information already collected in this phase:
{{phase_collected_data}}

Required information still missing:
{{phase_missing_required}}

Optional information not yet collected:
{{phase_missing_optional}}

---

CROSS-PHASE CONTEXT

{{cross_phase_context}}

---

TURN CONTEXT

Turn type: {{turn_type}}

{{turn_type_instructions}}

User's last message:
{{last_user_message}}

Fields needing clarification:
{{clarification_needed}}

---

CONVERSATION HISTORY
Conversation summary:
{{conversation_summary}}

Recent turns:
{{recent_turns}}

---

TASK
Based on the phase guidance and the current phase data:

1. If there is a user message to acknowledge, briefly acknowledge
   relevant information the user just provided.
2. If clarification is needed, ask for it naturally.
3. If no clarification is needed, ask the best next question to
   progress the phase.
4. If no required information remains:
   - Smoothly conclude this phase
   - Gently prompt the user forward based on phase guidance

---

IMPORTANT CONSTRAINTS
- Do NOT extract or summarize structured information.
- Do NOT mention "required" or "optional".
- Do NOT reference internal fields, schemas, or phase names.
- Do NOT decide or announce phase transitions.
- Do NOT include JSON, metadata, or analysis.
- Output ONLY the message to send to the user.
- No preamble. No sign-off unless the phase guidance says otherwise.

Generate the user-facing message now.
```

---

## Template Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `{{active_phase_name}}` | Active phase from state | Name of the currently active phase. Included for the LLM's internal reference — the Speaker should never say this name aloud. |
| `{{active_phase_speaker_md}}` | File: `skills/{active_phase}/speaker.md` | Full contents of the current phase's speaker skill file. Injected verbatim — never truncated. |
| `{{phase_collected_data}}` | Computed from state + schema | Non-null fields only. Formatted as natural key-value pairs using `display_name` from the schema, not raw JSON or field names. |
| `{{phase_missing_required}}` | Computed from state + schema | List of required field descriptions (not field names) that haven't been collected yet. |
| `{{phase_missing_optional}}` | Computed from state + schema | List of optional field descriptions not yet collected. |
| `{{cross_phase_context}}` | Computed by State Updater | Summary of relevant data from other phases. See Cross-Phase Context section. |
| `{{turn_type}}` | Determined by State Updater | One of: `first_turn`, `standard`, `phase_transition`, `clarification`, `entity_transition`. See Turn Types section. |
| `{{turn_type_instructions}}` | Determined by turn type | Additional instructions specific to the turn type. See Turn Types section. |
| `{{last_user_message}}` | Current turn input | The raw user message. Null on first turn. |
| `{{clarification_needed}}` | Set by State Updater | Field descriptions needing clarification due to conflicts or ambiguity. Null if none. |
| `{{conversation_summary}}` | `state.conversationSummary` | Cumulative summary of conversation history up to the last summarization point. Empty string early in conversation. See Skill 7. |
| `{{recent_turns}}` | `state.messages` (from `lastSummarizedTurnIndex`) | Recent conversation turns since the last summary, formatted as a simple transcript with `[User]` and `[Assistant]` labels. Same format used by all components. See Skill 7. |

### Formatting Collected Data

The Speaker should never see raw JSON or field names. Transform state into natural descriptions using `display_name` from the state schema.

**Bad — raw state:**
```json
{"target_company": "Google", "role_level": "senior"}
```

**Good — natural formatting:**
```
- Company: Google
- Role level: Senior
```

For each non-null field, look up the field's `display_name` from the schema. Format array values as comma-separated lists. If no fields are collected yet, output "Nothing collected yet."

### Formatting Missing Fields

Missing fields should be described by their purpose, not their technical names, using `description` from the state schema.

**Bad — field names:**
```
- role_title
- interview_format
```

**Good — natural descriptions:**
```
- The specific job title for the role
- The format of the interview (phone screen, coding, system design, etc.)
```

If no fields are missing, output "None — all collected."

### Formatting Clarification Needs

**Bad — technical:**
```
- target_company: conflict between "Google" and "Amazon"
```

**Good — natural:**
```
- Company: You mentioned both "Google" and "Amazon" — which one is
  the upcoming interview for?
```

### Entity-Bearing Phases

For phases with entity structure, format collected data to show the current entity's fields with a brief note about prior entities.

**Bad — dump all entities:**
```
- Project 1 Name: API Gateway
- Project 1 Role: Lead Engineer
- Project 1 Technologies: Go, gRPC
- Project 2 Name: Data Pipeline
- Project 2 Role: (not yet collected)
```

**Good — focus on current entity with prior summary:**
```
Current project (2 of 5):
- Project Name: Data Pipeline
- (Role and technologies not yet discussed)

Previously discussed:
- API Gateway (Lead Engineer)
```

The Speaker should focus on the current entity. Prior entities are summarized in one line each — just enough for conversational continuity, not enough to re-discuss.

For missing field lists, show only the current entity's missing fields:

**Bad:**
```
- Project 2 role
- Project 2 technologies
- Project 3 (not started)
```

**Good:**
```
- Your role on this project
- Technologies and tools you used
```

---

## Turn Types

The Speaker behaves differently depending on the context of the current turn. The `{{turn_type}}` and `{{turn_type_instructions}}` variables control this.

### First Turn (`first_turn`)

The very first turn of a phase when there's no user message to respond to. This happens at conversation start (first phase) or immediately after a phase transition.

**Turn type instructions:**
```
This is the first turn of this phase. There is no user message to
acknowledge. Use the phase's Opening Message guidance to generate
an appropriate greeting or introduction that begins collecting
information.
```

**Expected behavior:** The Speaker generates an opening message following the phase's speaker.md guidance. It should establish context and ask the first question.

### Standard Turn (`standard`)

A normal turn where the user has sent a message and the Analyzer has processed it.

**Turn type instructions:**
```
The user has provided a message. Acknowledge any new information,
then ask for the next missing field or guide toward completion.
```

**Expected behavior:** Acknowledge what the user said, then ask the next question or wrap up the phase.

### Phase Transition Turn (`phase_transition`)

A transition just occurred. The Speaker is generating the first message of the new phase, but unlike a cold `first_turn`, there's context from the previous phase to acknowledge.

**Turn type instructions:**
```
A phase transition just occurred. The user's last message was
processed in the previous phase. Smoothly transition to this new
phase by:
1. Briefly acknowledging the transition (without naming phases)
2. Using the phase's Opening Message guidance to introduce what
   comes next
3. Asking the first question for this phase

Previous phase context:
{{prior_phase_summary}}
```

**Expected behavior:** The Speaker bridges the gap between phases naturally. Example: "Great, I've got a good picture of your interview setup. Now let's get into some practice!"

### Clarification Turn (`clarification`)

The State Updater detected a conflict or ambiguity that needs user input before proceeding.

**Turn type instructions:**
```
The system needs clarification on specific information. Ask the user
to clarify naturally, without mentioning technical reasons or
field names.
```

**Expected behavior:** The Speaker asks for clarification naturally. Example: "Just want to make sure — are you interviewing at Google or Amazon? You mentioned both and I want to prep you for the right one."

### Entity Transition Turn (`entity_transition`)

The State Updater decided to rotate to the next entity within the current phase. The Speaker should close out the previous entity and open the next.

**Turn type instructions:**
```
An entity rotation just occurred within the current phase. The agent
has finished discussing one {{entity_display_name}} and is moving to
the next.

1. Briefly wrap up the previous entity (one sentence, not a full
   summary)
2. Transition naturally to the next entity
3. Ask the first question for the new entity using the phase's
   Opening Message guidance adapted for a mid-conversation tone
   (less formal than the phase opening since rapport is established)

Previous entities discussed:
{{prior_entities_summary}}

Current entity number: {{current_entity_number}} of {{max_entities}}
```

**Expected behavior:** The Speaker bridges between entities naturally. Example: "Great context on the API Gateway project. Do you have another project you'd like to walk me through?"

Note: `entity_transition` is similar to `phase_transition` but lighter. The tone stays the same (same phase), and the transition should feel like a continuation, not a reset. The Speaker should NOT summarize all fields from the previous entity — just acknowledge and move forward.

---

## Cross-Phase Context

When the Speaker is operating in a phase that benefits from knowing what previous phases collected, the State Updater provides cross-phase context.

### When to Include

- **Always on `phase_transition` turns** — the Speaker needs to know what the previous phase established.
- **When the phase's speaker.md references prior information** — e.g., the practice phase needs to know the company and role to frame questions.
- **Not on first turn of the first phase** — there's no prior context.

### Format

```
Information from previous phases:
- Company: Google
- Role: Senior Software Engineer
- Level: Senior
- Interview format: System design
- Technical focus: Distributed systems
```

Keep it concise — only include fields relevant to the current phase's communication. Which fields to surface is configured in `orchestrator_rules.md`.

### When Empty

```
No prior phase information available.
```

---

## Customization Points

### Via Phase Skill Files (Preferred)

Most communication behavior should live in the phase's `speaker.md` file: tone and style, questioning strategy, acknowledgment patterns, opening message guidance, edge case handling, phase completion language. Changing `speaker.md` files requires no template changes.

### Via Global Communication Rules (When Needed)

Modify the GLOBAL COMMUNICATION RULES section when the domain requires a fundamentally different communication approach:

- **"Always ask two questions per turn"** — for fast-paced triage bots where efficiency matters more than conversational flow.
- **"Never use technical jargon"** — for consumer-facing products.
- **"Include quick reply buttons"** — for chat UIs that support structured response options.

### Via Turn Types (Rare)

Add a new turn type only when the domain has a turn context not covered by the five defaults — e.g., an `error_recovery` turn where the system apologizes for a misunderstanding.

### What Should NEVER Be Customized

- The read-only relationship with state
- The prohibition on extracting information or deciding transitions
- The "no internals" constraint (field names, phase names, JSON)
- The natural language output requirement

---

## Test Categories

| Category | Setup | What to Check |
|----------|-------|---------------|
| **First turn** | turn_type=first_turn, empty collected, no user message | Generates opening message, asks first question, matches tone |
| **Standard — one field missing** | One required field missing | Asks for the missing field naturally |
| **Standard — multiple missing** | Several fields missing | Asks for one (or naturally grouped) fields, not all at once |
| **Standard — acknowledge + ask** | User just provided info, more fields missing | Acknowledges the new info, then asks next question |
| **Phase transition** | turn_type=phase_transition, prior_phase_summary present | Bridges naturally, introduces new phase, asks first question |
| **Clarification** | clarification_needed has entries | Asks for clarification naturally without mentioning conflicts |
| **All complete** | No missing required fields | Summarizes naturally, guides forward |
| **User asks question** | User message is a question, not info | Answers helpfully, then redirects to collection |
| **User goes off-topic** | User message is unrelated | Gentle redirect without being dismissive |
| **No internals leak** | Any context | Output contains no field names, phase names, JSON, or "required" |
| **Entity transition** | turn_type=entity_transition, prior_entities_summary present, current entity empty | Wraps up previous entity briefly, introduces new entity naturally, asks first question |

---

## Worked Examples

Each example shows only the variable sections that change — the system role, global rules, task, and constraints sections are always the same as the template above.

### Example 1: First Turn

**Variables:**
```
ACTIVE PHASE: interview_setup

PHASE DATA:
  Collected: Nothing collected yet.
  Missing required: Company, role title, seniority level, interview format
  Missing optional: Timeline, technical topics, preparation level

CROSS-PHASE CONTEXT: No prior phase information available.

TURN CONTEXT:
  Turn type: first_turn
  User's last message: (none)
  Clarification: (none)
```

**Expected output:**
> Hey! I'm here to help you prep for your interview. Let's get a few details so I can tailor the experience. First off — which company are you interviewing with?

### Example 2: Standard Turn (Acknowledge + Ask)

**Variables:**
```
ACTIVE PHASE: interview_setup

PHASE DATA:
  Collected: Company: Google | Role level: Senior | Timeline: Next week | Technical focus: Distributed systems
  Missing required: Role title, interview format
  Missing optional: Preparation level

TURN CONTEXT:
  Turn type: standard
  User's last message: "I have a Google interview next week for a senior backend role, probably distributed systems stuff."
  Clarification: (none)
```

**Expected output:**
> Nice, a senior backend role at Google focusing on distributed systems — exciting! Could you tell me the specific role title and what format the interview will be? For instance, is it a phone screen, system design round, coding round, or a full onsite loop?

### Example 3: Phase Transition

**Variables:**
```
ACTIVE PHASE: question_practice

PHASE DATA:
  Collected: Nothing collected yet.
  Missing required: Questions completed, user responses
  Missing optional: Topic focus

CROSS-PHASE CONTEXT:
  Company: Google | Role: Senior Software Engineer | Level: Senior
  Interview format: System design | Technical focus: Distributed systems

TURN CONTEXT:
  Turn type: phase_transition
  Previous phase context: Interview setup complete — Google, Senior SWE, system design round.
  User's last message: "I think it's called Senior Software Engineer, and it's going to be a system design round."
  Clarification: (none)
```

**Expected output:**
> Senior Software Engineer, system design round at Google — I've got the full picture. Let's jump into some practice! Here's your first one: How would you design a distributed key-value store that supports high availability and eventual consistency? Take your time and walk me through your approach.

### Example 4: Clarification

**Variables:**
```
ACTIVE PHASE: interview_setup

PHASE DATA:
  Collected: Company: Google | Role level: Senior
  Missing required: Role title, interview format
  Missing optional: Timeline, technical topics, preparation level

TURN CONTEXT:
  Turn type: clarification
  User's last message: "Actually I'm also talking to Amazon about a similar role."
  Clarification: Company — You mentioned both Google and Amazon. Which one would you like to focus on for this mock interview?
```

**Expected output:**
> Oh nice, both Google and Amazon — that's great to have options! For this mock interview, which one would you like to focus on? We can always do another round for the other one afterward.

### Example 5: Entity Transition

**Variables:**
```
ACTIVE PHASE: experience_review

PHASE DATA:
  Current project (2 of 3):
    Collected: Nothing collected yet.
    Missing required: Project name, your role, key contribution
    Missing optional: Technologies used
  Previously discussed:
    - API Gateway (Lead Engineer)

CROSS-PHASE CONTEXT:
  Company: Google | Role: Senior Software Engineer

TURN CONTEXT:
  Turn type: entity_transition
  Previous entities discussed: API Gateway (Lead Engineer)
  Current entity number: 2 of 3
  User's last message: "I also spent a lot of time on our data pipeline."
  Clarification: (none)
```

**Expected output:**
> Great stuff on the API Gateway work. You mentioned a data pipeline — tell me about that! What was the project about, and what was your role on it?

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Passing raw field names in missing_required | Speaker says "I still need your target_company" | Format as natural descriptions using `description` from the schema |
| Passing raw JSON as collected_data | Speaker references JSON structure | Format as natural key-value pairs using `display_name` from the schema |
| No turn_type distinction | First turns awkwardly try to acknowledge nonexistent user message | Use the turn type system with clear instructions per type |
| No cross-phase context on transitions | Speaker in new phase has no idea what was discussed before | State Updater assembles and injects cross-phase context |
| Including the full conversation transcript | Speaker repeats old acknowledgments, loses focus | Use conversation summary + recent turns (Skill 7), not the full transcript |
| Speaker.md truncated | Communication quality degrades; tone, edge cases lost | Never truncate — this is the Speaker's core instruction set |
| Clarification context uses technical language | Speaker tells user about "field conflicts" | Format clarification needs as natural questions |
| Not including optional fields as missing | Speaker never gently probes for useful optional info | Include missing_optional so Speaker can weave them in naturally |
| Entity transition message fully summarizes previous entity | Response is too long, feels repetitive | Brief wrap-up only — one sentence, not a field-by-field recap |
| Showing all entities' missing fields, not just current | User is confused about what's being asked | Only show current entity's missing fields |
| Entity transition tone is as formal as phase opening | Feels like a restart, breaks rapport | Use a lighter, continuation tone — rapport is already established |
