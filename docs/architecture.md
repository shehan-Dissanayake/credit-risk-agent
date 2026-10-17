# Architecture

Pipeline: data sources -> planning agent -> tools (quantitative, qualitative, knowledge/RAG,
loan history) -> verification agent -> cited risk memo + audit trail. The verifier can send the
case back to the planner when it finds unsupported claims (max 2 repair loops).

The full production spec (RAG pipeline, guardrails, agent orchestration, evaluation, security)
lives in the Production Design Doc. Keep this file as the short, code-adjacent summary and update
it when the implementation diverges from the spec.

## Layers

| Layer | Responsibility | Phase |
| --- | --- | --- |
| Ingestion | Parse, clean, chunk, attach metadata, index | 1 |
| Retrieval | Query understanding, hybrid search, rerank, quality gates | 1-2 |
| Guardrails | Input, retrieval-time and output checks | 2+ |
| Tools | Deterministic, typed, read-only functions | 3 |
| Agent | State graph, planner, verifier, escalation | 4-5 |
| Observability | Traces, metrics, audit memo | 0+ |
| Evaluation | Golden sets, baselines, regression gates | 1-6 |
| API / UI | FastAPI service and demo UI | 7 |
