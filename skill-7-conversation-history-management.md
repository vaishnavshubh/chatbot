# Skill 7: Conversation History Management

## Purpose

This skill defines how conversation history is managed and injected into the Analyzer and Speaker prompts. The core challenge: conversations grow longer every turn, but prompt context windows are finite. The solution is simple — summarize older turns periodically, and always include recent unsummarized turns in full.

This skill also defines the summary prompt template (`prompts/summary_template.md`), which is a framework artifact used by the summarization step at runtime.

---

## Core Principles

1. **State is the primary memory, history is supplementary.** The state schema captures everything that's been collected. History provides conversational context — tone, flow, what was discussed — not data. If you had perfect state, you could run the system with zero history. History makes it better, not possible.
2. **Keep history simple and uniform.** All components receive the same history format. The Analyzer uses it for extraction context; the Speaker uses it to avoid repeating itself. No per-component formatting needed.
3. **Recent turns matter most.** In a phase-based system, the most relevant context is almost always the last few turns. A message from 20 turns ago is rarely useful for extracting information from the current message.
4. **The current user message is never part of history.** The current user message is injected separately as `{{user_message}}`. History covers previous turns only.

---

## How History Works

Every prompt sent to the Analyzer or Speaker includes a history section. That history is assembled from two parts:

```
History = [cumulative summary] + [recent unsummarized turns]
```

**Cumulative summary:** A concise paragraph that captures the conversation so far. Starts empty. Updated periodically (every N turns, where N is set in the implementation config). Each update takes the previous summary plus the next batch of turns and produces a new summary.

**Recent unsummarized turns:** The raw conversation turns that have happened since the last summary was generated. Formatted as a simple transcript with `[User]` and `[Assistant]` labels — the same format everywhere.

The result: the LLM always has awareness of the full conversation (via the summary) plus detailed access to the most recent exchanges (via raw turns). Token usage stays bounded because older turns are compressed into the summary rather than accumulating indefinitely.

Two variables carry this into the Analyzer template (Skill 2), the Speaker template (Skill 3), and the Summary template:
- `{{conversation_summary}}` — the cumulative summary (same as `state.conversationSummary`)
- `{{recent_turns}}` — unsummarized turns since the last summary boundary

All three templates receive the same content in the same format. The history manager assembles it; the prompt-loader injects it.

### Summarization Timing

Summarization is triggered every N turns, where N is set in the implementation config. Summarization can also be triggered on phase transitions regardless of the turn count, if configured.

Summarization happens **after** the Speaker's response has been sent to the user. The user never waits for summarization — it runs between turns.

### What Gets Summarized

The summary should capture **interaction dynamics**, not collected data:

- User preferences, constraints, and concerns
- Key decisions and corrections
- Emotional tone and attitude shifts
- Any entities mentioned (names, dates, topics, companies)

The summary should **not** include:
- Verbatim quotes (paraphrase instead)
- Turn-by-turn narration ("then the user said...")
- Data that is already captured in the agent's state (the state tracks collected fields separately)

---

## History Format

All components receive the same history format — a labeled summary block followed by a simple transcript of recent turns:

```
[Conversation summary]: User expressed preference for
system design topics and mentioned being nervous about the
interview. User confirmed targeting Google for a Senior SWE role.

[User]: I think the format is a mix of coding and system design.
[Assistant]: Got it — a combined format. Is there a specific
system design topic you're most worried about?
[User]: Yeah, I'd prefer to focus on the system design part.
```

When the conversation summary is empty (early in conversation), only the recent turns appear. When there are no unsummarized turns (immediately after summarization), only the summary appears.

---

## Summary Prompt Template

This template lives at `agent_config/prompts/summary_template.md` alongside the analyzer and speaker templates. It is a framework artifact — the same template is used regardless of the domain.

```markdown
SYSTEM ROLE
You are a conversation summarizer. Your job is to produce a
concise updated summary of a conversation by combining prior
summaries with the latest exchange history.

---

INSTRUCTIONS
Analyze the past chat summaries and summarize the following
latest chat history concisely without losing any key entity
or information.

Preserve:
- User preferences, constraints, and concerns
- Key decisions and corrections
- Emotional tone and attitude shifts
- Any entities mentioned (names, dates, topics, companies)

Do not include:
- Verbatim quotes (paraphrase instead)
- Turn-by-turn narration ("then the user said...")
- Data that is already captured in the agent's state
  (the state tracks collected fields separately)

---

PAST SUMMARIES
{{conversation_summary}}

---

LATEST TURNS
{{recent_turns}}

---

OUTPUT
Produce a single concise summary paragraph that integrates
the past summaries with the latest history. If past summaries
are empty, summarize only the latest history.
```

### Template Variables

| Variable | Source | Description |
|---|---|---|
| `{{conversation_summary}}` | `state.conversationSummary` | The cumulative summary from all previous summarization runs. Empty string on the first summarization. |
| `{{recent_turns}}` | `state.messages` (from `lastSummarizedTurnIndex`) | The raw conversation turns since the last summary, formatted as a simple transcript with `[User]` and `[Assistant]` labels. |

---

## History at Phase Transitions

Phase transitions are natural compression points. When moving from phase A to phase B:

1. The detailed conversation from phase A becomes less relevant. The data it collected is in state. The tone and flow of its questions don't matter for phase B.
2. The Speaker gets cross-phase context from the Orchestrator, which provides the key data from phase A.
3. If configured, a summarization is triggered at this point regardless of the N-turn threshold, compressing the completed phase's conversation into the cumulative summary.

On a phase transition turn, the history includes the cumulative summary (which now covers the completed phase) plus any turns from the new phase.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Truncating the current user message | Analyzer can't extract from truncated input | The current user message is in `{{user_message}}`, separate from history — it is never part of the history section |
| Storing only user messages | Speaker doesn't know what it already said, repeats acknowledgments | Store both user and assistant messages |
| Including raw JSON or metadata in history | Confuses the LLM, degrades response quality | History should be clean conversation transcript |
| Summary lists collected data instead of interaction dynamics | Wastes summary space on data the state already tracks | Summary prompt emphasizes preferences, concerns, and tone — not field values |
| Summarization blocks the user response | User waits for summarization to complete before seeing the agent's reply | Summarization runs after the response is sent to the user, not before |
