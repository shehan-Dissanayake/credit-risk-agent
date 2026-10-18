# Decision log

One entry per significant choice: date, decision, options considered, evidence, outcome.

## ADR-0001: src layout, pyproject-only packaging
- Options: flat layout vs `src/` layout.
- Decision: `src/` layout, hatchling build backend, no setup.py. Prevents accidental imports from the repo root and matches modern Python practice.

## ADR-0002: Own lightweight tracer before Langfuse
- Options: adopt Langfuse immediately vs write a minimal JSONL tracer first.
- Decision: minimal tracer now (spans, parent ids, attributes, status). Record shape mirrors OpenTelemetry/Langfuse so export is a later adapter, not a rewrite.

## ADR-0003: Dependencies added per phase
- Decision: Phase 0 installs only API, config and dev tooling. LangGraph, Qdrant client, embedding and reranker libraries arrive with the phase that needs them, each with a log entry.

## ADR-0004: Supabase (Postgres + pgvector) instead of Qdrant
- Options: Qdrant plus separate Postgres, vs a single Postgres with pgvector on Supabase.
- Decision: one database for vectors, metadata, financial tables, cases and traces. Hybrid search is a SQL function (dense cosine + Postgres full-text, fused with RRF). Schema is versioned as SQL migrations run by `cra migrate`.
- Trade-offs: Postgres full-text ranking is not classic BM25, and HNSW with metadata filters can return fewer candidates than requested. Both are measured in the Phase 2 ablation; revisit if lexical recall is weak.
- Security: RLS enabled on all tables with no policies; backend uses a privileged connection; secrets only in `.env`.

## ADR-0005: Sentence Transformers for local embeddings
- Decision: use the configured `CRA_EMBEDDING_MODEL` through Sentence Transformers, truncating output to `CRA_EMBEDDING_DIM` (1024 by default).
- Rationale: supports the default `BAAI/bge-m3` model without adding a hosted embedding API or another credential requirement; loading stays lazy until indexing is requested.
- Trade-off: the selected model must be available through Sentence Transformers, and first use may download model weights.

## To decide (fill with evidence during the build)
- Chunk size and strategy
- Embedding model
- Reranker
- Retrieval thresholds
- Step budget
- Confidence formula
