# Building Conversational Agents with Skills 1–10: A Student Overview

## What Is This System?

Skills 1–10 are a structured method for building **multi-phase conversational agents** — AI chatbots that collect information from users through natural conversation, phase by phase, rather than through forms or single prompts.

Think of it like designing an interview. The agent guides the user through a series of conversation stages (called **phases**), collecting specific pieces of information in each one, then moving on when it has what it needs.

The current framework focuses on information collection. The same architecture — Analyzer proposes, Orchestrator decides, Speaker communicates — can extend to agents that also **take actions** (calling APIs, looking up data, running tools) during the conversation. This document covers the collection framework; tool calling, ReAct loops, and MCP integration are covered separately.

The system has three layers:

- **Framework skills** (reusable regardless of what chatbot you're building): the prompt templates and execution engine
- **Generated skills** (unique to your chatbot): the configuration files and phase-specific instructions that define what *your* chatbot does
- **Skill 10** (the meta-skill): the process that takes your requirements and generates all the chatbot-specific files

---

## The Five Nodes at Runtime

Every turn in a conversation runs through five nodes in sequence. Three are "intelligent" (they do conceptual work) and two are "assembly" nodes (they prepare prompts):

```
User message
    │
    ▼
┌──────────────────────────┐
│ Analyzer Prompt Creator   │  Loads the analyzer template + phase skill,
│ (assembly — no LLM call)  │  injects state into {{placeholders}}
└─────────┬────────────────┘
          │ assembled prompt
          ▼
┌──────────────────────────┐
│ Analyzer                  │  Sends the prompt to the LLM,
│ (LLM call)                │  returns a JSON extraction
└─────────┬────────────────┘
          │ proposed state delta
          ▼
┌──────────────────────────┐
│ Orchestrator              │  Validates extraction, merges into state,
│ (deterministic — no LLM)  │  decides: stay / advance / complete
└─────────┬────────────────┘
          │ updated state + turn type
          ▼
┌──────────────────────────┐
│ Speaker Prompt Creator    │  Loads the speaker template + phase skill,
│ (assembly — no LLM call)  │  injects state into {{placeholders}}
└─────────┬────────────────┘
          │ assembled prompt
          ▼
┌──────────────────────────┐
│ Speaker                   │  Sends the prompt to the LLM,
│ (LLM call)                │  returns the user-facing message
└──────────────────────────┘
          │
          ▼
     Agent response
```

The three conceptual roles are:
- **Analyzer** — reads the user's message, proposes extracted data as JSON
- **Orchestrator** — the deterministic brain; validates, merges state, applies business rules, decides transitions. (The implementation file is called `state-updater.ts` to emphasize that it makes no LLM calls — but its job is orchestration.)
- **Speaker** — generates the next natural-language reply

Each has a clear, non-overlapping job. The Analyzer never talks to the user. The Speaker never extracts data. The Orchestrator is the only one that touches state. The two Prompt Creator nodes exist to cleanly separate "deciding what goes in the prompt" from "calling the LLM."

### First-Turn Exception

On the very first turn, there is no user message to analyze. The Analyzer Prompt Creator, Analyzer, and the extraction steps are skipped. The Orchestrator sets the default phase and marks the turn as `first_turn`, then flow goes straight to the Speaker Prompt Creator → Speaker, which generates the conversation's opening message.

### Phase Redirect Loop

Sometimes the user says something that belongs to a different phase. When the Analyzer detects this, it suggests a phase change. Before the Orchestrator processes the extraction, the system loops back to the Analyzer Prompt Creator, which rebuilds the prompt for the *suggested* phase so the Analyzer can re-extract the user's message with the correct phase's instructions:

```
Analyzer ──(phase changed)──→ Analyzer Prompt Creator ──→ Analyzer (retry)
                                                              │
                                                      (phase confirmed)
                                                              │
                                                              ▼
                                                        Orchestrator
```

This loop runs at most twice. If the Analyzer keeps changing its mind after two redirects, the system stops, asks the user to rephrase, and moves on.

> **Future extension: Tool Calling.** The framework's "Analyzer proposes, Orchestrator decides" pattern extends naturally to actions. An Analyzer can propose a tool call (just as it currently proposes phase transitions). The Orchestrator validates and approves it. A Tool Executor runs it. The Speaker presents the result. The pipeline becomes:
>
> ```
> Analyzer → Orchestrator → Tool Executor → Speaker
> ```
>
> (with Prompt Creator nodes on either side, as in the current pipeline)
>
> For multi-step reasoning (ReAct), the Tool Executor loops with a Reasoner until it has enough information, then hands off to the Speaker. For external tool protocols (MCP), the Tool Executor acts as the MCP client. In all cases, the core principle holds: no component both interprets user intent *and* makes control decisions. The Analyzer reads. The Orchestrator decides. New components execute.

---

## What Each Skill Does

### How the Workflow Actually Works

You don't need to read or navigate Skills 1–9 yourself. **Cursor uses Skill 10 as its instruction set.** Skill 10 tells Cursor how to walk you through your requirements, generate a plan for your chatbot, and then produce all the configuration files by drawing on Skills 1–9 as needed.

Your job is to:
1. **Describe what your chatbot should do** (provide requirements)
2. **Review and approve the plan** Cursor generates (give feedback, confirm decisions)
3. **Review the generated files** and refine if needed

Cursor's job is to:
1. Follow Skill 10's seven-stage process
2. Consult Skills 1–9 at the right moments to produce high-quality output
3. Validate everything is consistent before delivering the final files

That said, understanding what each skill covers helps you give better feedback and spot issues in the generated output. Here's the breakdown.

### Configuration Skills (what gets built for your chatbot)

| Skill | Name | What It Produces | Cursor Uses It When... |
|-------|------|-----------------|------------------------|
| **4** | State Schema Design | `state_schema.json` | Defining what data your chatbot collects |
| **5** | Phase Registry Design | `phase_registry.json` | Defining conversation phases and transitions |
| **6** | Orchestrator Rules | `orchestrator_rules.md` | Defining business logic, limits, and runtime behavior |
| **1** | Phase Skill Authoring | `analyzer.md` + `speaker.md` per phase | Writing extraction and communication instructions |

### Framework Skills (reusable templates)

| Skill | Name | What It Produces | Cursor Uses It When... |
|-------|------|-----------------|------------------------|
| **2** | Analyzer Prompt Engineering | `prompts/analyzer_template.md` | Ensuring phase skills don't duplicate built-in rules |
| **3** | Speaker Prompt Engineering | `prompts/speaker_template.md` | Ensuring phase skills don't duplicate built-in rules |
| **7** | Conversation History Management | `prompts/summary_template.md` | Compressing older conversation turns into summaries |

### Operational Skills (quality and reliability)

| Skill | Name | What It Covers | Cursor Uses It When... |
|-------|------|---------------|------------------------|
| **7** | Conversation History | Summarization and history management (also produces the framework template listed above) | Configuring how much conversation context to keep |
| **8** | Error Recovery | Error catalog and recovery strategies | Configuring how failures are handled |
| **9** | Testing and Debugging | Validation checks and test cases | Verifying everything works before delivery |

### The Meta-Skill (what drives the whole process)

| Skill | Name | What It Does |
|-------|------|-------------|
| **10** | Domain Customization | Tells Cursor how to orchestrate all 9 skills above |

---

## What the Final Output Looks Like

After running through Skill 10's generation process, you get a complete folder:

```
project/
├── framework/
│   └── skills/
│       ├── <skill-1.md - skill-10.md files>
│       └── implementation_spec.md          ← this file
│
agent_config/
├── state_schema.json              ← Every field the agent collects
├── phase_registry.json            ← All phases and how they connect
├── orchestrator_rules.md          ← Business rules and runtime config
│
├── skills/
│   ├── phase_one/
│   │   ├── analyzer.md            ← How to extract data in this phase
│   │   └── speaker.md             ← How to talk to the user in this phase
│   ├── phase_two/
│   │   ├── analyzer.md
│   │   └── speaker.md
│   └── ... (one folder per phase)
│
├── prompts/
│   ├── analyzer_template.md       ← Framework template (not custom)
│   ├── speaker_template.md        ← Framework template (not custom)
│   └── summary_template.md        ← Framework template (not custom)
│
└── tests/
    ├── fixtures/
    │   └── synthetic_conversations.json
    └── validate_config.ts
```

### What each file does:

**`state_schema.json`** — The contract. It lists every piece of information the agent can collect, organized by phase. Each field has a type, a required/optional flag, an update policy (overwrite, append, or flag conflicts), and a human-readable display name so the Speaker never exposes internal field names.

**`phase_registry.json`** — The map. It declares which phases exist, what order they go in, which transitions are allowed, and under what conditions. It does *not* list fields — that's the schema's job.

**`orchestrator_rules.md`** — The rulebook. Written in plain English, it defines the default phase flow, cross-phase context (what data carries forward between phases), business rules (domain-specific constraints), transition confidence thresholds, conversation limits, error tolerance, fallback messages, resumption config, and optional hooks (extension points for custom logic at key moments in the pipeline).

**`skills/{phase}/analyzer.md`** — Extraction instructions for one phase. Lists every field to look for, how to interpret ambiguous input, what *not* to extract, and when the phase is complete.

**`skills/{phase}/speaker.md`** — Communication instructions for one phase. Defines tone, questioning strategy, opening message guidance, how to acknowledge information, and what to say when the phase is done.

**`prompts/analyzer_template.md`**, **`prompts/speaker_template.md`**, and **`prompts/summary_template.md`** — Framework templates that wrap the phase-specific files at runtime. The analyzer and speaker templates provide global rules (like "extract only what's explicit" and "never mention field names") so you don't repeat them in every phase. The summary template drives periodic conversation summarization to keep prompt sizes bounded (see Skill 7).

---

## How to Use This System: Step by Step

### Step 1: Describe Your Chatbot

Start by telling Cursor what your chatbot should do. At minimum, answer three questions:

1. **What is the chatbot's purpose?** (one sentence)
2. **What information does it need to collect?** (list of data points)
3. **What does it do with the collected information?** (output or action)

A fuller requirements description also covers: target users, conversation flow, constraints, tone, edge cases, and what happens when collection is complete. See Skill 10 for the ideal requirements template. The more detail you provide, the better the first draft will be — but even a short paragraph is enough to get started.

### Step 2: Review the Plan (Skill 10, Stages 1–2)

Cursor will generate a concrete plan before building anything:

- How many phases the conversation needs
- What fields go in each phase
- A transition map (which phase leads to which)
- Assumptions it's making and decisions that could go either way

**Your job here is to react.** Does the phase structure make sense? Are there missing data points? Is the flow logical? Give feedback, and Cursor will revise before moving on.

### Step 3: Cursor Generates Everything (Skill 10, Stages 3–6)

Once you approve the plan, Cursor works through the generation pipeline, consulting Skills 1–9 as needed:

- **Stage 3–4:** Analyzes your requirements and designs the phases
- **Stage 5:** Builds the three config files — state schema (Skill 4), phase registry (Skill 5), and orchestrator rules (Skill 6, informed by Skills 7 and 8)
- **Stage 6:** Writes the phase skill files — `analyzer.md` and `speaker.md` for each phase (Skill 1, informed by Skills 2 and 3)

### Step 4: Cursor Validates (Skill 10, Stage 7)

Cursor runs Skill 9's pre-deployment checks automatically:

1. **File completeness** — every phase has both skill files
2. **Registry integrity** — all transitions are valid, all phases are reachable
3. **Schema consistency** — field names match across all files
4. **Template variables** — placeholders are present in all templates
5. **Business rule references** — rules point to real phases and fields

These checks are deterministic (no LLM calls) and are encoded in `agent_config/tests/validate_config.ts`.

Separately, a runtime smoke test (`src/tests/smoke-test.ts`, defined by the implementation spec) initializes the chatbot, triggers the opening message, sends a simple user message, and confirms it responds without crashing. This test *does* make LLM calls and validates the full 5-node pipeline.

### Step 5: Review and Refine

The generated files are a high-quality first draft, not a finished product. Review them with domain knowledge:

- Do the `analyzer.md` files cover how your users actually talk? Are synonym mappings realistic?
- Does the `speaker.md` tone match what you want?
- Are the business rules capturing real constraints from your domain?
- Are edge cases covered (what if the user refuses to answer, goes off-topic, or contradicts themselves)?

You can edit the files directly or ask Cursor to revise specific sections.

---

## Key Rules to Remember

**Field names are contracts.** A field name must be identical across `state_schema.json`, `analyzer.md`, `speaker.md`, and `orchestrator_rules.md`. One typo = silent failure.

**Don't duplicate what the framework provides.** The analyzer and speaker templates already handle global rules (extract only explicit info, never mention field names, etc.). Your phase skills add domain-specific detail on top.

**Phase skills have separate concerns.** `analyzer.md` is for extraction only — no tone guidance. `speaker.md` is for communication only — no extraction rules.

**State is the primary memory.** The state schema captures everything collected. Conversation history is supplementary context, not the source of truth.

**Every phase needs 2–6 fields.** Fewer than 2 means it should merge with another phase. More than 6 means it should split. Keep required fields to 2–4.

**Test the seams.** The most common bugs happen at handoff points — Analyzer output into Orchestrator merge, Orchestrator state into Speaker Prompt Creator context assembly. Test the full 5-node pipeline, not just individual components.

---

## Quick Reference: Which Skill Does What

You don't need to consult these directly — Cursor handles that. But if you want to understand what's behind a generated file or give more targeted feedback, here's where to look:

| You're reviewing... | The relevant skill is |
|---------------------|----------------------|
| What fields the chatbot collects and their types | Skill 4 (State Schema) |
| How phases connect and transition | Skill 5 (Phase Registry) |
| How the chatbot extracts data from user messages | Skill 1 (Phase Skill Authoring) + Skill 2 (Analyzer Template) |
| How the chatbot talks to the user | Skill 1 (Phase Skill Authoring) + Skill 3 (Speaker Template) |
| Business rules and runtime config | Skill 6 (Orchestrator Rules) |
| How conversation history is managed | Skill 7 (History Management) |
| How errors and edge cases are handled | Skill 8 (Error Recovery) |
| How the chatbot is validated and tested | Skill 9 (Testing & Debugging) |
| The end-to-end generation process | Skill 10 (Domain Customization) |
