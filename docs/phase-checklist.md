# Phase checklist

Move to the next phase only when every box in the current one is ticked, or the gap is accepted in `decision-log.md`.

## Phase 0: Foundations
- [x] Repo layout and packaging (`pyproject.toml`, src layout)
- [x] Typed settings with agent budgets
- [x] Tracing skeleton writing JSONL spans
- [x] CLI smoke test (`cra hello-trace`)
- [x] Health endpoint and tests
- [x] Lint, format, type check, tests wired into CI
- [ ] CI green on GitHub (after first push)
- [ ] Pre-commit hooks installed locally

## Phase 1: Data and RAG baseline
- [ ] Corpus chosen and documented
- [ ] Ingestion with full chunk metadata
- [ ] Dense-only retrieval
- [ ] Golden set v1
- [ ] Baseline retrieval metrics recorded

## Phase 2: Production RAG
- [ ] Hybrid search plus reranker
- [ ] Query pipeline (understanding, rewriting, decomposition, routing)
- [ ] Quality gates (relevance, sufficiency, corrective retry, conflicts)
- [ ] Guardrails tested with injection and PII samples
- [ ] Ablation table with measured gains

## Phase 3: Tools
- [ ] Quantitative tool with unit tests against known values
- [ ] Qualitative tool with structured output
- [ ] Knowledge (RAG) tool
- [ ] Loan history tool (read-only)
- [ ] All tool outputs validated

## Phase 4: Agent core
- [ ] Typed state graph with hard budgets
- [ ] Planner with evidence checklist
- [ ] Memo with citations and audit trail
- [ ] 10 cases end to end with full traces

## Phase 5: Verification and human-in-the-loop
- [ ] Separate verifier call
- [ ] Repair loop (max 2) and escalation paths
- [ ] Confidence calibration check
- [ ] Verifier catches at least 90 percent of seeded errors

## Phase 6: Evaluation and hardening
- [ ] 30 to 50 labelled cases with hold-out
- [ ] Baselines: rule scorecard, single LLM call
- [ ] Adversarial tests (injection, missing, stale, conflicting data)
- [ ] Cost and latency report

## Phase 7: Packaging
- [ ] Streamlit or React demo
- [ ] Docker Compose runs the full stack
- [ ] README with ablation table and eval results
- [ ] Demo video
