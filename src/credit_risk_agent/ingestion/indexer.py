"""Generate embeddings and idempotently load documents and chunks into Postgres."""

from __future__ import annotations

import math
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow

from credit_risk_agent.config import get_settings
from credit_risk_agent.db import connect
from credit_risk_agent.ingestion.chunker import ParentChunk, chunk_document
from credit_risk_agent.ingestion.parser import Document, parse_document


@dataclass(frozen=True)
class IndexResult:
    document_id: UUID
    inserted: bool
    parent_chunks: int
    child_chunks: int


def generate_embeddings(
    texts: list[str],
    *,
    model_name: str | None = None,
    dimension: int | None = None,
    batch_size: int = 32,
) -> list[list[float]]:
    """Encode texts in batches using the configured Sentence Transformers model."""
    settings = get_settings()
    selected_model = model_name or settings.embedding_model
    selected_dimension = dimension or settings.embedding_dim
    if selected_dimension < 1:
        raise ValueError("Embedding dimension must be positive")
    if batch_size < 1:
        raise ValueError("Embedding batch_size must be positive")
    if not texts:
        return []

    try:
        sentence_transformers = import_module("sentence_transformers")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Embedding support is not installed; install the project dependencies "
            "to use the index command"
        ) from exc

    encoder: Any = sentence_transformers.SentenceTransformer(
        selected_model,
        truncate_dim=selected_dimension,
    )
    encoded: Any = encoder.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    to_list = getattr(encoded, "tolist", None)
    vectors: Any = to_list() if callable(to_list) else encoded
    if len(vectors) != len(texts):
        raise ValueError("Embedding model returned a different number of vectors than inputs")

    result: list[list[float]] = []
    for vector in vectors:
        values = [float(value) for value in vector]
        if len(values) != selected_dimension:
            raise ValueError(
                f"Embedding model returned {len(values)} dimensions; "
                f"expected {selected_dimension}"
            )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Embedding model returned a non-finite value")
        result.append(values)
    return result


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


def load_document(
    connection: psycopg.Connection[TupleRow],
    document: Document,
    parents: tuple[ParentChunk, ...],
    *,
    title: str,
) -> IndexResult:
    """Insert a document and its parent/child chunks, skipping known content hashes."""
    if not document.company:
        raise ValueError("Document metadata must include a company")

    inserted_row = connection.execute(
        """
        insert into documents (
            company_id, doc_type, title, trust_level, as_of_date, fiscal_year, content_hash
        ) values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (content_hash) do nothing
        returning id
        """,
        (
            document.company,
            document.doc_type,
            title,
            "unverified",
            document.as_of_date,
            document.fiscal_year,
            document.content_hash,
        ),
    ).fetchone()
    if inserted_row is None:
        existing_row = connection.execute(
            "select id from documents where content_hash = %s",
            (document.content_hash,),
        ).fetchone()
        if existing_row is None:
            raise RuntimeError("Content hash conflict occurred but the document could not be found")
        return IndexResult(UUID(str(existing_row[0])), False, 0, 0)

    document_id = UUID(str(inserted_row[0]))
    parent_ids: dict[int, UUID] = {}
    for parent in parents:
        row = connection.execute(
            """
            insert into chunks (document_id, parent_id, chunk_index, content, token_count)
            values (%s, null, %s, %s, %s)
            returning id
            """,
            (document_id, parent.index, parent.content, parent.token_count),
        ).fetchone()
        if row is None:
            raise RuntimeError("Database did not return an id for a parent chunk")
        parent_ids[parent.index] = UUID(str(row[0]))

    child_chunks = [child for parent in parents for child in parent.children]
    vectors = generate_embeddings([child.content for child in child_chunks])
    for child, vector in zip(child_chunks, vectors, strict=True):
        connection.execute(
            """
            insert into chunks (
                document_id, parent_id, chunk_index, content, token_count, embedding
            ) values (%s, %s, %s, %s, %s, %s::extensions.vector)
            """,
            (
                document_id,
                parent_ids[child.parent_index],
                len(parents) + child.index,
                child.content,
                child.token_count,
                _vector_literal(vector),
            ),
        )

    return IndexResult(document_id, True, len(parents), len(child_chunks))


def index_file(path: Path) -> IndexResult:
    """Parse and index a UTF-8 Markdown/text file using the configured database."""
    raw_text = path.read_text(encoding="utf-8")
    document = parse_document(raw_text)
    if not document.company:
        raise ValueError("Document metadata must include a company (for example, company: Acme)")
    parents = chunk_document(document)
    with connect() as connection:
        return load_document(connection, document, parents, title=path.stem)
