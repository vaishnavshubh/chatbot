# RAG source documents

Place **Markdown** files here (`.md`). Each file name (without extension) becomes the chunk **`topic`** field and must match a `goal.primary_goal` value, for example:

- `financial_foundations.md`
- `budget_cashflow.md`
- `credit_management.md`
- `workplace_401k.md`
- `student_loans.md`
- `borrowing_basics.md`

Use `## Section Title` for chunk boundaries. Run:

```bash
python app/rag/ingest.py
```

to regenerate `data/rag_index/chunks.jsonl`.
