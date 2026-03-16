# Orchestrator Rules

The orchestrator is the **deterministic control layer** of the chatbot. It owns the conversation state, validates all analyzer outputs, controls phase transitions, and dispatches instructions to the speaker. No LLM call may alter the conversation phase or state directly — only the orchestrator can.

---

## 1. Core Responsibilities

| Responsibility | Description |
|---|---|
| **State ownership** | The orchestrator holds the single source of truth: the state object defined by `state_schema.json`. |
| **Analyzer validation** | Every fact extracted by the analyzer is validated against the schema before being written to state. Invalid or out-of-range values are rejected. |
| **Phase gating** | A phase advances only when all its `exit_conditions` (defined in `phase_registry.json`) are satisfied. |
| **Speaker dispatch** | The orchestrator passes the current phase, state snapshot, and list of missing fields to the speaker so it knows what to ask next. |
| **Artifact triggering** | After Phase 4, the orchestrator checks artifact trigger conditions and invokes the Artifact Renderer when appropriate. |

---

## 2. Phase Transition Rules

### 2.1 Forward-Only Progression
Phases progress strictly forward: 0 → 1 → 2 → 3 → 4 → 5. The orchestrator never moves backward to a prior phase.

### 2.2 Exit Condition Evaluation
Before advancing from phase N to phase N+1, the orchestrator checks every exit condition for phase N as defined in `phase_registry.json`.

```
function canAdvance(currentPhase, state):
    for condition in phase_registry[currentPhase].exit_conditions:
        if not evaluate(condition, state):
            return false
    return true
```

### 2.3 Phase 3 — Dynamic Required Fields
Phase 3 is unique: its required fields depend on the value of `goal.primary_goal`. The orchestrator must:
1. Look up `required_fields_by_goal[state.goal.primary_goal]` from the phase registry.
2. Use that list as the effective required fields for Phase 3.
3. If the goal has no required fields (e.g., `financial_foundations`, `borrowing_basics`), the phase may exit after the speaker confirms the user has no additional context to share.

### 2.4 Skip Handling in Phase 3
If the user explicitly declines to provide evidence ("I don't know my APR", "Let's skip this"), the orchestrator:
1. Notes the skip in state.
2. Advances to Phase 4 with whatever data is available.
3. Instructs the speaker to acknowledge the skip and explain that the plan will be more general.

### 2.5 Max Turn Guard
Each phase defines a `max_turns` count. If the orchestrator has spent `max_turns` conversation turns in a single phase without satisfying exit conditions, it:
1. Logs the incomplete fields.
2. Delivers the phase's `fallback_message` via the speaker.
3. Gives the user one more opportunity to provide the missing information.
4. If still incomplete, proceeds with available data and notes the gap.

---

## 3. Analyzer Validation Rules

### 3.1 Schema Conformance
Every field extracted by the analyzer must match the type, enum, and range constraints defined in `state_schema.json`.

| Validation | Rule |
|---|---|
| **Enum fields** | Value must be one of the allowed enum values. If not, reject and ask the speaker to clarify. |
| **Numeric fields** | Must be a valid number within `minimum` and `maximum` bounds. |
| **String fields** | Must be a non-empty string. |
| **Boolean fields** | Must be `true` or `false`. |

### 3.2 Conflict Resolution
If the analyzer extracts a value for a field that is already populated and the new value differs, the orchestrator:
1. Keeps the **new** value (latest user input wins).
2. Instructs the speaker to confirm the change: "Just to confirm, you'd like to update your [field] from [old] to [new]?"

### 3.3 Out-of-Phase Extraction
If the analyzer extracts a field that belongs to a future phase (e.g., user mentions their APR during Phase 1), the orchestrator:
1. Stores the value in state immediately (information should never be discarded).
2. Does **not** skip ahead to that phase.
3. Continues processing the current phase's required fields.

---

## 4. Speaker Dispatch Protocol

Each turn, the orchestrator provides the speaker with a structured instruction payload:

```json
{
  "current_phase": 1,
  "phase_display_name": "Baseline Profile",
  "populated_fields": ["profile.life_stage", "profile.pay_type"],
  "missing_fields": ["profile.pay_frequency", "profile.income_range"],
  "state_snapshot": { ... },
  "instruction": "Ask the user about their pay frequency and income range. Be conversational and non-judgmental."
}
```

The speaker must:
- Address only the missing fields for the current phase.
- Never ask about fields from future phases.
- Never reveal internal field names to the user.
- Use natural language, not schema terminology.

---

## 5. Goal-Specific Evidence Requirements

When the orchestrator enters Phase 3, it loads the appropriate field set based on the selected goal:

| Goal | Required Evidence Fields |
|---|---|
| `financial_foundations` | *(none — qualitative conversation)* |
| `budget_cashflow` | `budget.fixed_expenses`, `budget.variable_expenses` |
| `credit_management` | `credit.apr`, `credit.balance`, `credit.minimum_payment` |
| `workplace_401k` | `retirement.employer_match`, `retirement.contribution_rate` |
| `student_loans` | `loan.principal`, `loan.interest_rate`, `loan.payment_amount` |
| `borrowing_basics` | *(none — qualitative conversation)* |

Optional fields (e.g., `credit.due_date`) are collected if volunteered but never block phase advancement.

---

## 6. Artifact Generation Rules

### 6.1 Timing
Artifacts may **only** be generated after `plan_generated == true` (Phase 4 completion).

### 6.2 Trigger Conditions

| Artifact | Condition |
|---|---|
| PDF Summary | `output_preference == "pdf"` |
| CSV Budget Template | `goal.primary_goal == "budget_cashflow"` |
| Chart | `output_preference == "charts"` AND at least one numeric evidence field is populated |

### 6.3 Renderer Contract
The Artifact Renderer receives a read-only copy of the state and the generated plan text. It produces deterministic output — no LLM calls.

---

## 7. Safety Rules

### 7.1 Product Recommendation Guard
The orchestrator monitors speaker output for:
- Specific product names (credit card brands, brokerage names, fund tickers)
- Phrases like "you should invest in", "I recommend", "the best card is"

If detected, the orchestrator **blocks** the response and substitutes:
> "I can explain what to look for when evaluating [product category], but I'm not able to recommend a specific product."

### 7.2 Advice Disclaimer
The speaker must include an educational disclaimer at least once during Phase 0 and reinforce it if the user asks for specific advice:
> "This is educational information, not personalized financial advice. Consider consulting a qualified financial advisor for decisions specific to your situation."

### 7.3 Data Sensitivity
- The chatbot must never ask for Social Security numbers, full account numbers, or passwords.
- If a user volunteers sensitive data, the orchestrator instructs the speaker to acknowledge it was received but advise the user not to share such information in chat.

### 7.4 Scope Boundaries
If a user asks about a topic outside the six supported goals, the speaker acknowledges the question and gently redirects:
> "That's an important topic, but it's outside what I can cover today. Would you like to focus on one of these areas instead: budgeting, credit, 401(k), student loans, financial foundations, or borrowing basics?"

---

## 8. Error Handling

| Scenario | Orchestrator Action |
|---|---|
| Analyzer returns empty or malformed JSON | Re-run the analyzer once. If still invalid, ask the speaker to rephrase the question. |
| User message is off-topic or unintelligible | Increment an off-topic counter. After 2 consecutive off-topic messages, deliver a gentle redirect via the speaker. |
| Network or LLM failure | Return a graceful error message: "I'm having trouble processing that. Could you try again?" |
| User requests to restart | Reset state to initial values. Return to Phase 0. |

---

## 9. Orchestrator Loop (Pseudocode)

```
function handleUserMessage(message, state):
    phase = phase_registry[state.current_phase]
    
    // Step 1: Analyze
    extracted = analyzer.run(message, phase.skills.analyzer, state)
    
    // Step 2: Validate & merge
    for field, value in extracted:
        if isValid(field, value, state_schema):
            state = updateState(state, field, value)
        else:
            log("Rejected invalid value", field, value)
    
    // Step 3: Check phase advancement
    if canAdvance(state.current_phase, state):
        state.current_phase += 1
        phase = phase_registry[state.current_phase]
    
    // Step 4: Build speaker instruction
    missing = getMissingFields(state.current_phase, state)
    instruction = buildSpeakerPayload(phase, state, missing)
    
    // Step 5: Generate response
    response = speaker.run(instruction, phase.skills.speaker)
    
    // Step 6: Artifact check (Phase 4 only)
    if state.plan_generated and hasArtifactTriggers(state):
        artifacts = artifactRenderer.run(state)
        response = appendArtifacts(response, artifacts)
    
    return response, state
```
