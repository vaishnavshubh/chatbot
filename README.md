# Financial Literacy Chatbot

A phase-based conversational chatbot that helps early-career professionals learn about budgeting, credit, 401(k), student loans, and more. Built for MGMT 590 Emerging Technologies in Business.

**Default LLM:** **Gemma 4** — hosted via the [Gemini API](https://ai.google.dev/gemma) (`GEMINI_API_KEY` + `LLM_MODEL`, default `gemma-4-26b-a4b-it`), or locally via Ollama (`gemma4:latest` and `OPENAI_BASE_URL`). See **Configure the LLM** below.

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

### 2. Configure the LLM

```bash
cp .env.example .env
```

**Google Gemini API + Gemma 4 (hosted):** Set `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey) and `LLM_MODEL` to a Gemma 4 id (e.g. `gemma-4-26b-a4b-it`, `gemma-4-31b-it`). The app uses the `google-genai` SDK. Do not set `OPENAI_BASE_URL` for this path.

**Local Gemma 4 (Ollama):** Comment out `GEMINI_API_KEY`, install [Ollama](https://ollama.com), run `ollama pull gemma4:latest`, then set `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama`, and `LLM_MODEL` to the tag from `ollama list`.

**OpenAI cloud:** No `GEMINI_API_KEY`; set a real `OPENAI_API_KEY`, leave `OPENAI_BASE_URL` unset, and set `LLM_MODEL` to an OpenAI model id (e.g. `gpt-4o-mini`).

### 3. Run the chatbot

```bash
streamlit run app/streamlit_app.py
```

The app opens at `http://localhost:8501`.

Restart Streamlit after changing `.env` (the LLM backend is cached on first load).

## Gemini API vs OpenAI-compatible

- **Gemini API:** If `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set, requests go through [`google-genai`](https://github.com/googleapis/python-genai) (`app/llm_backend.py`). Set `LLM_MODEL` to the hosted Gemma / Gemini id you want.
- **OpenAI or Ollama:** Unset `GEMINI_API_KEY`, set `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL` for Ollama). Same phase logic; only the HTTP client changes.

## Local models (Ollama)

1. Install Ollama and pull an image: `ollama pull gemma4:latest` (see [Ollama library](https://ollama.com/library/gemma4)).
2. `ollama list` → copy the tag into `LLM_MODEL`.
3. `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama`.

If the Analyzer’s JSON is flaky, try a larger model or lower temperature in `app/llm_backend.py` / `app/analyzer.py`.

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
