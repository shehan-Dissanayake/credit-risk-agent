# Credit Risk Investigation Agent

An autonomous agent that investigates a borrower or company, combines quantitative ratios with
qualitative signals (news, filings), and produces a **cited, auditable risk memo**. A separate
verification agent checks every claim against the evidence, and the system escalates to a human
whenever evidence is missing, stale or conflicting.

> Status: **Phase 0 (foundations)**. See `docs/phase-checklist.md` for progress.

## Design principles

1. Evidence over fluency: every claim links to a source or tool result.
2. Deterministic code for maths, validation and policy; LLM for planning, reading and writing.
3. Bounded autonomy: hard limits on steps, tokens, time and cost; read-only tools.
4. Measure before trusting: retrieval, groundedness and risk accuracy all have numbers.
5. Fail safe: insufficient evidence means escalate, never guess.
6. Observable and reproducible: full traces, versioned prompts, pinned configs.
7. The agent recommends; a human decides.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
make install            # installs dev deps and pre-commit hooks
cp .env.example .env
make check              # lint + type check + tests (same as CI)
make hello-trace        # writes a sample trace to ./traces
make run                # API at http://localhost:8000/health
```

## Repository layout

```
src/credit_risk_agent/
  ingestion/       parsing, chunking, indexing            (Phase 1)
  retrieval/       query pipeline, hybrid search, gates   (Phase 1-2)
  tools/           quant, qualitative, knowledge, loans   (Phase 3)
  agent/           state graph, planner, verifier, memo   (Phase 4-5)
  guardrails/      input, retrieval and output checks     (Phase 2+)
  observability/   tracing, metrics, audit                (Phase 0+)
  api/             FastAPI app
  config.py        typed settings and agent budgets
prompts/           versioned prompt files + changelog
configs/           per-environment config files
evals/             golden sets, eval scripts, reports
tests/             unit and integration tests
docs/              architecture, decision log, phase checklist
data/              raw and processed corpus (git-ignored)
```

## Development workflow

- Run `make check` before every push. CI runs the same steps.
- Add dependencies only when a phase needs them, and record the reason in `docs/decision-log.md`.
- Never commit `.env`, data files or traces.
- Any change to prompts, chunking or retrieval must be accompanied by an eval run (from Phase 2).
