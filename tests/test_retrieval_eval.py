from evals.evaluate_retrieval import (
    RetrievalHit,
    _citation_identifier_groups,
    compute_metrics,
)


def test_compute_metrics_uses_unique_document_rank_order() -> None:
    hits = [
        RetrievalHit(document_id="uuid-1", title="unrelated"),
        RetrievalHit(document_id="uuid-2", title="sample-borrower-001-fy2024-filing"),
        RetrievalHit(document_id="uuid-3", title="also-unrelated"),
    ]

    precision, recall, reciprocal_rank, relevant_retrieved = compute_metrics(
        hits,
        [
            {
                "sample-borrower-001-fy2024-filing",
                "sample-borrower-001-fy2024-filing.pdf",
            }
        ],
        k=2,
    )

    assert precision == 0.5
    assert recall == 1.0
    assert reciprocal_rank == 0.5
    assert relevant_retrieved == 1


def test_citation_identifier_groups_preserve_all_citations() -> None:
    groups = _citation_identifier_groups(
        [
            {"document_id": "document-one", "source": "document-one.pdf"},
            {"document_id": "document-two"},
        ]
    )

    assert groups == [
        {"document-one", "document-one.pdf"},
        {"document-two"},
    ]
