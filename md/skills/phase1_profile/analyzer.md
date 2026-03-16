# Analyzer — Phase 1: Baseline Profile

## Purpose

Extract four structured facts about the user's employment and financial context from their message.

---

## Input

The user's raw message text and the current conversation state.

## Output

Return a JSON object with only the fields that can be confidently extracted.

```json
{
  "life_stage": "new_graduate",
  "pay_type": "salaried",
  "pay_frequency": "biweekly",
  "income_range": "50k_75k"
}
```

---

## Extraction Rules

### life_stage (string enum)

The user's current career stage.

| Value | User signals |
|---|---|
| `"student"` | "I'm still in school", "I'm a college student", "undergrad", "grad student" |
| `"new_graduate"` | "Just graduated", "I'm a recent grad", "finished school last year", "class of 2025" |
| `"early_career"` | "Been working for a few years", "I've been at my job for 2 years", "started my career", "working full-time" |
| `"career_changer"` | "Switching careers", "going back to school", "starting over in a new field", "transitioning" |

If the user says something like "I just started my first job after college," extract `"new_graduate"`.

### pay_type (string enum)

How the user is compensated.

| Value | User signals |
|---|---|
| `"salaried"` | "I'm salaried", "I make $X per year", "annual salary" |
| `"hourly"` | "I'm paid hourly", "I make $X per hour", "$15/hr" |
| `"freelance"` | "I freelance", "self-employed", "contract work", "gig work", "1099" |
| `"stipend"` | "I get a stipend", "fellowship", "assistantship", "it's a fixed stipend" |

### pay_frequency (string enum)

How often the user receives a paycheck.

| Value | User signals |
|---|---|
| `"weekly"` | "Every week", "paid weekly", "every Friday" |
| `"biweekly"` | "Every two weeks", "biweekly", "every other Friday", "26 paychecks a year" |
| `"semi_monthly"` | "Twice a month", "1st and 15th", "semi-monthly", "24 paychecks a year" |
| `"monthly"` | "Once a month", "monthly", "end of the month", "12 paychecks" |

**Common confusion:** "Biweekly" (every 2 weeks, 26 pay periods) vs. "semi-monthly" (twice per month, 24 pay periods). If the user says "twice a month" use `"semi_monthly"`. If they say "every two weeks" use `"biweekly"`.

### income_range (string enum)

Approximate annual gross income bracket.

| Value | User signals |
|---|---|
| `"under_25k"` | "Less than 25k", "around 20 thousand", "part-time income" |
| `"25k_50k"` | "About 30k", "35 thousand", "around 45k" |
| `"50k_75k"` | "I make about 60k", "55 thousand a year", "around 70k" |
| `"75k_100k"` | "About 80k", "I make 90 thousand", "just under six figures" |
| `"over_100k"` | "Over 100k", "I make 120 thousand", "six figures" |

If the user gives an hourly rate, estimate the annual income:
- hourly_rate × 40 hours × 52 weeks = approximate annual income
- Then map to the appropriate range.

If the user gives a monthly income, multiply by 12 and map.

---

## Multi-Fact Extraction

Users often provide multiple facts in a single message. Extract all recognizable facts.

**Example:** "I just graduated and got a salaried job paying about 55k. I get paid every two weeks."

Extract:
```json
{
  "life_stage": "new_graduate",
  "pay_type": "salaried",
  "pay_frequency": "biweekly",
  "income_range": "50k_75k"
}
```

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User gives exact salary ($62,000) | Map to `"50k_75k"` range |
| User gives hourly rate ($18/hr) | Calculate ~$37,440/year → `"25k_50k"` |
| User says "I'm between jobs" | Extract `life_stage` as `"career_changer"` if context supports it; omit `pay_type` and `pay_frequency` |
| User says "it varies" for income | Omit `income_range` — speaker should ask for a rough estimate |
| User gives net (after-tax) income | Still map to the closest range; the categories are approximate |
| User mentions multiple income sources | Map to total combined approximate income |

---

## Validation Contract

The orchestrator will reject:
- `life_stage` values not in `["student", "new_graduate", "early_career", "career_changer"]`
- `pay_type` values not in `["salaried", "hourly", "freelance", "stipend"]`
- `pay_frequency` values not in `["weekly", "biweekly", "semi_monthly", "monthly"]`
- `income_range` values not in `["under_25k", "25k_50k", "50k_75k", "75k_100k", "over_100k"]`

Only extract what is clearly stated or can be confidently inferred. When in doubt, omit the field.
