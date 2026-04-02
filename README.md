# Financial Literacy Chatbot

A phase-based conversational chatbot that helps early-career professionals learn about budgeting, credit, 401(k), student loans, and more. Built for MGMT 590 Emerging Technologies in Business.

## Architecture

The system separates AI reasoning from deterministic logic:

| Component | Type | Role |
|---|---|---|
| **Analyzer** | LLM | Extracts structured facts from user messages |
| **Orchestrator** | Code | Maintains state, validates data, controls phase transitions |
| **Speaker** | LLM | Generates conversational responses |
| **Artifact Renderer** | Code | Produces PDF summaries |
| **RAG (retrieval)** | Code | Loads curated chunks; **Phase 4** plan grounding via keyword retrieval |

See **`Rag_implementation.md`** (and `Rag_implementation.html`) for full RAG documentation.

## Conversation Phases

0. **Consent & Setup** — Explain scope, confirm consent, set output preference
1. **Baseline Profile** — Employment situation and income range
2. **Goal Selection** — Pick a financial topic and time horizon
3. **Evidence Intake** — Collect relevant financial numbers
4. **Plan Generation** — Generate a structured educational plan
5. **Follow-up** — Commit to a concrete next action

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
cp .env.example .env
# Edit .env and paste your key
```

### 3. Run the chatbot

```bash
streamlit run app/streamlit_app.py
```

The app opens at `http://localhost:8501`.

## Project Structure

```
chatbot/
├── app/
│   ├── streamlit_app.py      # Streamlit UI entry point
│   ├── orchestrator.py       # Core conversation loop
│   ├── state.py              # Pydantic state models
│   ├── phase_registry.py     # Phase definitions & advancement logic
│   ├── analyzer.py           # LLM fact extraction
│   ├── speaker.py            # LLM response generation
│   ├── validator.py          # Field validation
│   ├── pdf_generator.py      # PDF artifact renderer
│   └── rag/                  # RAG: ingest, retrieval, prompts
├── data/
│   ├── rag/                  # Source Markdown for RAG (edit here)
│   └── rag_index/
│       └── chunks.jsonl      # Built chunk index (run app/rag/ingest.py)
├── md/
│   ├── domain_brief.md       # Project specification
│   ├── state_schema.json     # State schema (JSON Schema)
│   ├── phase_registry.json   # Phase definitions
│   ├── orchestrator_rules.md # Orchestrator rule set
│   └── skills/               # LLM skill prompts (analyzer + speaker per phase)
├── Rag_implementation.md     # RAG design & operations
├── requirements.txt
├── .env.example
└── README.md
```

## Supported Topics

- Financial Foundations
- Budget & Cash Flow
- Credit Management
- Workplace 401(k)
- Student Loans
- Borrowing Basics

## Scope

This chatbot provides **educational guidance only**. It never recommends specific financial products, investments, or credit cards.
