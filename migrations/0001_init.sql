-- 0001_init: documents, chunks, hybrid search (dense + full-text, fused with RRF)
-- Portable between Supabase and a plain pgvector Postgres.

create schema if not exists extensions;
create extension if not exists vector with schema extensions;
set search_path = public, extensions;

-- ---------------------------------------------------------------- documents
create table if not exists documents (
    id            uuid primary key default gen_random_uuid(),
    company_id    text not null,
    doc_type      text not null check (doc_type in ('filing', 'transcript', 'policy', 'news')),
    title         text not null,
    source_url    text,
    trust_level   text not null check (trust_level in ('official', 'reputable', 'unverified')),
    as_of_date    date,
    version       integer not null default 1,
    content_hash  text not null unique,   -- idempotent ingestion
    ingested_at   timestamptz not null default now()
);

create index if not exists documents_lookup_idx
    on documents (company_id, doc_type, as_of_date);

-- ------------------------------------------------------------------- chunks
-- Small-to-big: child chunks carry embeddings; parent chunks (sections) are returned
-- as context. NOTE: vector(1024) must match the embedding model chosen in Phase 1.
create table if not exists chunks (
    id             uuid primary key default gen_random_uuid(),
    document_id    uuid not null references documents (id) on delete cascade,
    parent_id      uuid references chunks (id) on delete set null,
    chunk_index    integer not null,
    section_title  text,
    page           integer,
    content        text not null,
    token_count    integer,
    embedding      vector(1024),
    fts            tsvector generated always as (to_tsvector('english', content)) stored,
    created_at     timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create index if not exists chunks_document_idx on chunks (document_id);
create index if not exists chunks_embedding_hnsw
    on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_fts_gin on chunks using gin (fts);

-- ----------------------------------------------------------------- security
-- RLS on with no policies: Supabase API roles (anon/authenticated) see nothing.
-- Our backend connects with a privileged role that bypasses RLS.
alter table documents enable row level security;
alter table chunks    enable row level security;

-- ------------------------------------------------------------ hybrid search
-- Reciprocal Rank Fusion of dense (cosine) and lexical (Postgres full-text) rankings.
-- Metadata filters are applied inside both legs.
create or replace function hybrid_search(
    query_text       text,
    query_embedding  vector(1024),
    match_count      int     default 8,
    candidate_count  int     default 30,
    filter_company   text    default null,
    filter_doc_types text[]  default null,
    rrf_k            int     default 60
)
returns table (
    chunk_id     uuid,
    document_id  uuid,
    content      text,
    rrf_score    double precision,
    dense_pos    int,
    lexical_pos  int
)
language sql
stable
set search_path = public, extensions
as $$
    with dense as (
        select c.id,
               row_number() over (order by c.embedding <=> query_embedding) as pos
        from chunks c
        join documents d on d.id = c.document_id
        where c.embedding is not null
          and (filter_company is null or d.company_id = filter_company)
          and (filter_doc_types is null or d.doc_type = any (filter_doc_types))
        order by c.embedding <=> query_embedding
        limit candidate_count
    ),
    lexical as (
        select c.id,
               row_number() over (
                   order by ts_rank_cd(c.fts, websearch_to_tsquery('english', query_text)) desc
               ) as pos
        from chunks c
        join documents d on d.id = c.document_id
        where c.fts @@ websearch_to_tsquery('english', query_text)
          and (filter_company is null or d.company_id = filter_company)
          and (filter_doc_types is null or d.doc_type = any (filter_doc_types))
        order by ts_rank_cd(c.fts, websearch_to_tsquery('english', query_text)) desc
        limit candidate_count
    )
    select c.id,
           c.document_id,
           c.content,
           coalesce(1.0 / (rrf_k + dense.pos), 0) + coalesce(1.0 / (rrf_k + lexical.pos), 0),
           dense.pos::int,
           lexical.pos::int
    from dense
    full outer join lexical on lexical.id = dense.id
    join chunks c on c.id = coalesce(dense.id, lexical.id)
    order by 4 desc
    limit match_count;
$$;