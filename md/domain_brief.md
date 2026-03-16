# Financial Literacy Chatbot — Domain Brief

## Mission

In one session, help an early-career professional understand and organize **one** core financial area — budgeting, credit, 401(k), student loans, or borrowing — and produce a structured educational action plan they can act on immediately.

The chatbot provides **educational guidance only**. It never provides personalized financial, tax, investment, or legal advice.

---

## Target User

- Recent college graduates entering the workforce
- Early-career professionals (0–5 years of experience)
- Individuals navigating their first paycheck, first credit card, first 401(k), or first loan repayment

---

## System Architecture

The system separates AI reasoning from deterministic logic using four components:

| Component | Type | Responsibility |
|---|---|---|
| **Analyzer** | LLM | Extracts structured facts from user messages into the state schema |
| **Orchestrator** | Code | Maintains state, validates analyzer output, controls phase transitions |
| **Speaker** | LLM | Generates conversational responses and asks targeted follow-up questions |
| **Artifact Renderer** | Code | Produces deterministic outputs: PDF summaries, CSV templates, charts |

### Data Flow

```
User Message
    ↓
Analyzer (LLM) → extracts facts → structured JSON
    ↓
Orchestrator (Code) → validates facts → updates state → selects next phase
    ↓
Speaker (LLM) → generates response using state + phase instructions
    ↓
User (+ optional Artifact Renderer output)
```

---

## Supported Financial Topics

| Topic Key | Display Name | Description |
|---|---|---|
| `financial_foundations` | Financial Foundations | Emergency funds, net worth basics, financial goal-setting |
| `budget_cashflow` | Budget & Cash Flow | Income vs. expenses, 50/30/20 rule, cash flow tracking |
| `credit_management` | Credit Management | Credit scores, APR, utilization, payment strategies |
| `workplace_401k` | Workplace 401(k) | Employer match, contribution rates, fund basics, vesting |
| `student_loans` | Student Loans | Federal vs. private, repayment plans, refinancing concepts |
| `borrowing_basics` | Borrowing Basics | Types of loans, interest rates, debt-to-income ratio |

---

## Inputs the Bot Must Collect

### Phase 0 — Consent & Setup
| Field | Purpose |
|---|---|
| `consent_acknowledged` | User confirms they understand this is educational only |
| `output_preference` | Preferred output format(s): chat, pdf, csv, charts |

### Phase 1 — Baseline Profile
| Field | Purpose |
|---|---|
| `life_stage` | Student, new graduate, early career, career changer |
| `pay_type` | Salaried, hourly, freelance, stipend |
| `pay_frequency` | Weekly, biweekly, semi-monthly, monthly |
| `income_range` | Approximate annual income bracket |

### Phase 2 — Goal Selection
| Field | Purpose |
|---|---|
| `primary_goal` | One of the six supported financial topics |
| `time_horizon` | Short-term (< 6 months), medium-term (6–24 months), long-term (2+ years) |

### Phase 3 — Evidence Intake (goal-dependent)

**Budget & Cash Flow:**
| Field | Purpose |
|---|---|
| `fixed_expenses` | Rent, utilities, subscriptions, insurance |
| `variable_expenses` | Food, entertainment, transportation |

**Credit Management:**
| Field | Purpose |
|---|---|
| `apr` | Annual percentage rate on primary card or debt |
| `balance` | Current outstanding balance |
| `minimum_payment` | Minimum monthly payment |
| `due_date` | Payment due date |

**Workplace 401(k):**
| Field | Purpose |
|---|---|
| `employer_match` | Employer match percentage or formula |
| `contribution_rate` | Current or planned employee contribution rate |

**Student Loans:**
| Field | Purpose |
|---|---|
| `principal` | Outstanding loan principal |
| `interest_rate` | Interest rate on the loan |
| `payment_amount` | Current monthly payment |

**Financial Foundations & Borrowing Basics:**
No specific numeric evidence required. The speaker gathers qualitative context through conversation.

### Phase 4 — Plan Generation
No new user input. The system generates the plan from collected state.

### Phase 5 — Follow-up
| Field | Purpose |
|---|---|
| `selected_next_action` | A concrete action the user commits to taking |

---

## Outputs

### Primary Output: Educational Action Plan
1. **Situation Summary** — Reflects the user's profile and goal back to them
2. **Key Concepts** — Defines relevant financial terms and frameworks
3. **Step-by-Step Checklist** — Actionable steps ordered by priority
4. **Risks & Pitfalls** — Common mistakes to avoid
5. **30-Day Action Plan** — Concrete tasks with a weekly cadence

### Optional Artifact Outputs
| Artifact | Format | When Generated |
|---|---|---|
| Plan Summary | PDF | After Phase 4, if user requested |
| Budget Template | CSV | When goal is `budget_cashflow` |
| Comparison Chart | Image/Chart | When numeric evidence supports visualization |

---

## Scope Boundaries

### The chatbot WILL:
- Explain financial concepts in plain language
- Teach decision-making frameworks (e.g., "how to evaluate whether to contribute more to a 401(k)")
- Generate structured checklists and action plans
- Provide general educational information about financial products as categories

### The chatbot will NEVER:
- Recommend specific stocks, bonds, mutual funds, or ETFs
- Recommend specific credit cards, banks, or financial products
- Provide personalized tax calculations or tax advice
- Provide legal advice or interpret regulations
- Store or transmit sensitive financial data (SSN, account numbers)
- Make predictions about market performance

When a user asks for specific product recommendations, the chatbot must redirect:
> "I can explain what to look for when comparing [product category], but I'm not able to recommend a specific one. Here's a framework for evaluating your options..."

---

## Conversation Phases

| Phase | Name | Goal |
|---|---|---|
| 0 | Consent & Setup | Explain scope, confirm consent, set output preference |
| 1 | Baseline Profile | Understand employment and financial context |
| 2 | Goal Selection | Identify primary financial topic and time horizon |
| 3 | Evidence Intake | Collect financial numbers or qualitative context |
| 4 | Plan Generation | Generate structured educational plan |
| 5 | Follow-up | Encourage commitment to a concrete next action |

Phases are strictly sequential. The orchestrator advances only when all required fields for the current phase are populated.
