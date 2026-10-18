from credit_risk_agent.ingestion.chunker import chunk_document
from credit_risk_agent.ingestion.parser import parse_document


def test_parse_document_extracts_metadata_and_stable_hash() -> None:
    raw = """---
company: Acme Corp
doc_type: filing
fiscal_year: 2024
as_of_date: 2025-02-14
---

# Annual report

Revenue increased by 8%.
"""

    first = parse_document(raw)
    second = parse_document(raw)

    assert first.company == "Acme Corp"
    assert first.doc_type == "filing"
    assert first.fiscal_year == 2024
    assert first.as_of_date is not None
    assert first.as_of_date.isoformat() == "2025-02-14"
    assert first.content_hash == second.content_hash
    assert first.content == "# Annual report\n\nRevenue increased by 8%."


def test_chunk_document_respects_parent_child_limits_and_overlap() -> None:
    content = "\n\n".join(
        f"Section {section}. " + " ".join(f"metric{index}" for index in range(75))
        for section in range(8)
    )
    document = parse_document(content)
    parents = chunk_document(
        document,
        parent_max_tokens=120,
        child_max_tokens=30,
        overlap_tokens=5,
    )

    assert len(parents) > 1
    assert all(parent.token_count <= 120 for parent in parents)
    for parent in parents:
        assert parent.children
        assert all(child.token_count <= 30 for child in parent.children)
        assert all(child.parent_index == parent.index for child in parent.children)
        for previous, current in zip(parent.children, parent.children[1:], strict=False):
            previous_tokens = previous.content.split()
            current_tokens = current.content.split()
            assert previous_tokens[-5:] == current_tokens[:5]
