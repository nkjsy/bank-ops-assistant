# Bank Ops Assistant

A small bank customer-service agent built with **LangChain**, featuring **RAG**, **tool calling**, **human approval** and an **eval set**. All data is fictional.

A learning project for getting familiar with the core concepts of AI agents. It is not a production system.

## What it can do

| Capability | How it works |
|---|---|
| Answer account questions (balances, transactions, spending totals by category) | The agent calls tools over SQLite; totals are computed by SQL, never by mental math in the model |
| Answer policy questions (fees, dispute deadlines, lost cards, transfer limits, overdrafts) | **RAG**: policy markdown is chunked, embedded and stored in Chroma; the agent retrieves with `search_policy` and cites its sources |
| Help customers file a transaction dispute | `create_dispute_ticket` is a write operation and requires **human approval** before it runs (LangChain `HumanInTheLoopMiddleware`) |
| No unauthorized access | Every tool is bound to the current customer and can only see their own accounts; input also goes through PII redaction and injection-hint detection |
| Measurable | `eval/golden.jsonl` has 16 cases that check the tools called, the answer content, whether data leaked, and whether the DB was really written after approval |

```
User question -> input guardrails (redaction / injection hints) -> LangChain agent (DeepSeek or other model)
              ├─ list_accounts / list_transactions / spending_summary   (SQLite, read-only, scoped to current customer)
              ├─ search_policy                                          (RAG: Chroma + policy docs)
              └─ create_dispute_ticket  --pauses for human approval--> writes to DB only if approved
```

## Quick start

For detailed step-by-step instructions from zero, see [GUIDE.md](GUIDE.md). The shortest version:

```bash
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
copy .env.example .env          # then put your DEEPSEEK_API_KEY in .env
python -m pytest -q             # no key needed; confirm the environment works first
python -m bankbot --customer C001
python eval/run_eval.py         # needs a key
```

## Layout

```
src/bankbot/
  config.py      paths, fixed date, model name
  data_gen.py    generates fictional data (including "storyline transactions" for evals)
  rag.py         chunk -> embed -> Chroma -> retrieve
  tools.py       the agent's tools (bound to the current customer)
  guardrails.py  PII redaction, injection-hint detection
  llm.py         creates the model from .env (switch models by changing config only)
  agent.py       assembles the agent + approval + tool-trace extraction
  cli.py         command-line chat
docs/policies/   policy docs used by RAG (fictional)
eval/            golden.jsonl eval set + run_eval.py
tests/           tests that need no API key (use a fake model)
```

## Limitations

- The data and policies are fictional; the embedding model is a small general-purpose one, and the eval set is tiny, so it only illustrates the method.
- The guardrails are basic (regex + tool scoping + approval), not a complete security solution.
