"""Evaluate dense retrieval against the versioned retrieval golden set."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypedDict, cast

import psycopg
from psycopg.rows import TupleRow

from credit_risk_agent.config import get_settings
from credit_risk_agent.db import connect
from credit_risk_agent.ingestion.indexer import generate_embeddings


class Citation(TypedDict, total=False):
    document_id: str
    source: str


class MetadataFilters(TypedDict, total=False):
    company_id: str
    doc_type: str
    as_of_date: str


class GoldenCase(TypedDict):
    case_id: str
    question: str
    target_ground_truth_citations: list[Citation]
    metadata_filters: MetadataFilters


class GoldenSet(TypedDict, total=False):
    dataset_id: str
    version: int
    synthetic: bool
    description: str
    cases: list[GoldenCase]


@dataclass(frozen=True)
class RetrievalHit:
    document_id: str
    title: str


@dataclass(frozen=True)
class CaseMetrics:
    case_id: str
    question: str
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    relevant_count: int
    relevant_retrieved: int
    retrieved: list[dict[str, str | bool]]


_DENSE_SEARCH_SQL = """
    select d.id::text, d.title
    from chunks c
    join documents d on d.id = c.document_id
    where c.embedding is not null
      and (%s::text is null or d.company_id = %s)
      and (%s::text is null or d.doc_type = %s)
      and (%s::date is null or d.as_of_date = %s)
    group by d.id, d.title
    order by min(c.embedding <=> %s::extensions.vector)
    limit %s
"""


def load_golden_set(path: Path) -> GoldenSet:
    """Load the benchmark JSON and verify the fields needed for scoring."""
    data = cast(GoldenSet, json.loads(path.read_text(encoding="utf-8")))
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Golden set {path} must contain at least one case")
    for case in cases:
        if not case.get("case_id") or not case.get("question"):
            raise ValueError("Each golden case must contain case_id and question")
        if not case.get("target_ground_truth_citations"):
            raise ValueError(f"Golden case {case['case_id']} has no target citations")
    return data


def _normalize_identifier(value: str) -> str:
    return value.strip().replace("\\", "/").casefold()


def _citation_identifier_groups(citations: list[Citation]) -> list[set[str]]:
    groups: list[set[str]] = []
    for citation in citations:
        identifiers: set[str] = set()
        document_id = citation.get("document_id")
        if document_id:
            identifiers.add(_normalize_identifier(document_id))
        source = citation.get("source")
        if source:
            source_path = Path(source.replace("\\", "/"))
            identifiers.add(_normalize_identifier(source_path.name))
            identifiers.add(_normalize_identifier(source_path.stem))
        if identifiers:
            groups.append(identifiers)
    return groups


def _hit_identifiers(hit: RetrievalHit) -> set[str]:
    title = _normalize_identifier(hit.title)
    title_stem = _normalize_identifier(Path(hit.title).stem)
    return {_normalize_identifier(hit.document_id), title, title_stem}


def _matched_citations(hit: RetrievalHit, relevant_groups: list[set[str]]) -> set[int]:
    identifiers = _hit_identifiers(hit)
    return {index for index, group in enumerate(relevant_groups) if identifiers & group}


def compute_metrics(
    hits: list[RetrievalHit], relevant_groups: list[set[str]], k: int
) -> tuple[float, float, float, int]:
    """Return Precision@K, Recall@K, reciprocal rank, and relevant count."""
    if k < 1:
        raise ValueError("k must be positive")
    if not relevant_groups:
        raise ValueError("At least one relevant citation identifier is required")

    ranked = hits[:k]
    matched_groups: set[int] = set()
    relevant_ranks: list[int] = []
    for rank, hit in enumerate(ranked, start=1):
        matched = _matched_citations(hit, relevant_groups)
        if matched:
            relevant_ranks.append(rank)
            matched_groups.update(matched)
    relevant_retrieved = len(matched_groups)
    precision = len(relevant_ranks) / k
    recall = relevant_retrieved / len(relevant_groups)
    reciprocal_rank = 1 / relevant_ranks[0] if relevant_ranks else 0.0
    return precision, recall, reciprocal_rank, relevant_retrieved


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


def search_dense(
    connection: psycopg.Connection[TupleRow],
    query_vector: list[float],
    filters: MetadataFilters,
    *,
    candidate_count: int,
) -> list[RetrievalHit]:
    """Return unique documents ordered by their closest dense chunk."""
    company_id = filters.get("company_id")
    doc_type = filters.get("doc_type")
    as_of_date = filters.get("as_of_date")
    rows = connection.execute(
        _DENSE_SEARCH_SQL,
        (
            company_id,
            company_id,
            doc_type,
            doc_type,
            as_of_date,
            as_of_date,
            _vector_literal(query_vector),
            candidate_count,
        ),
    ).fetchall()
    return [RetrievalHit(document_id=str(row[0]), title=str(row[1])) for row in rows]


def evaluate(
    golden_set: GoldenSet,
    *,
    k: int = 5,
    candidate_count: int = 100,
    connection: psycopg.Connection[TupleRow] | None = None,
) -> dict[str, Any]:
    """Run dense retrieval for every case and return the complete report object."""
    if candidate_count < k:
        raise ValueError("candidate_count must be greater than or equal to k")
    cases = golden_set["cases"]
    vectors = generate_embeddings([case["question"] for case in cases])
    if len(vectors) != len(cases):
        raise ValueError("Embedding model returned a different number of query vectors")

    owns_connection = connection is None
    active_connection = connection or connect()
    try:
        case_results: list[CaseMetrics] = []
        for case, query_vector in zip(cases, vectors, strict=True):
            citations = case["target_ground_truth_citations"]
            relevant_groups = _citation_identifier_groups(citations)
            hits = search_dense(
                active_connection,
                query_vector,
                case.get("metadata_filters", {}),
                candidate_count=candidate_count,
            )
            precision, recall, reciprocal_rank, relevant_retrieved = compute_metrics(
                hits, relevant_groups, k
            )
            retrieved: list[dict[str, str | bool]] = [
                {
                    "document_id": hit.document_id,
                    "title": hit.title,
                    "relevant": bool(_matched_citations(hit, relevant_groups)),
                }
                for hit in hits[:k]
            ]
            case_results.append(
                CaseMetrics(
                    case_id=case["case_id"],
                    question=case["question"],
                    precision_at_k=precision,
                    recall_at_k=recall,
                    reciprocal_rank=reciprocal_rank,
                    relevant_count=len(citations),
                    relevant_retrieved=relevant_retrieved,
                    retrieved=retrieved,
                )
            )
    finally:
        if owns_connection:
            active_connection.close()

    count = len(case_results)
    settings = get_settings()
    summary = {
        "precision_at_k": sum(result.precision_at_k for result in case_results) / count,
        "recall_at_k": sum(result.recall_at_k for result in case_results) / count,
        "mean_reciprocal_rank": sum(result.reciprocal_rank for result in case_results) / count,
    }
    return {
        "dataset_id": golden_set.get("dataset_id", "unknown"),
        "dataset_version": golden_set.get("version"),
        "synthetic": golden_set.get("synthetic", False),
        "description": golden_set.get("description", ""),
        "retrieval": "dense cosine similarity, unique documents ranked by closest chunk",
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "k": k,
        "candidate_count": candidate_count,
        "case_count": count,
        "summary": summary,
        "cases": [asdict(result) for result in case_results],
    }


def _print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(f"Dense retrieval baseline: {report['dataset_id']} (v{report['dataset_version']})")
    print(f"Model: {report['embedding_model']} ({report['embedding_dim']} dimensions)")
    print(f"Cases: {report['case_count']} | K: {report['k']}")
    print(f"Precision@{report['k']}: {summary['precision_at_k']:.4f}")
    print(f"Recall@{report['k']}:    {summary['recall_at_k']:.4f}")
    print(f"MRR:          {summary['mean_reciprocal_rank']:.4f}")
    for case in report["cases"]:
        print(
            f"  {case['case_id']}: P@K={case['precision_at_k']:.4f}, "
            f"R@K={case['recall_at_k']:.4f}, RR={case['reciprocal_rank']:.4f}"
        )
    if report["synthetic"]:
        print("WARNING: this golden set is synthetic; metrics are illustrative, not corpus-backed.")


def main(argv: list[str] | None = None) -> int:
    evals_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Benchmark dense retrieval against a golden set")
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=evals_dir / "golden_sets" / "v1_golden_set.json",
    )
    parser.add_argument(
        "--output", type=Path, default=evals_dir / "reports" / "phase1_baseline.json"
    )
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--candidate-count", type=int, default=100)
    args = parser.parse_args(argv)

    golden_set = load_golden_set(args.golden_set)
    report = evaluate(golden_set, k=args.k, candidate_count=args.candidate_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _print_summary(report)
    print(f"Report saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
