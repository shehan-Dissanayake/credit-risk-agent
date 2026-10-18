from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from credit_risk_agent.ingestion.indexer import generate_embeddings, load_document
from credit_risk_agent.ingestion.parser import parse_document


def test_generate_embeddings_uses_configured_model_and_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    class FakeEncoder:
        def __init__(self, model_name: str, *, truncate_dim: int) -> None:
            calls["model_name"] = model_name
            calls["truncate_dim"] = truncate_dim

        def encode(self, texts: list[str], **kwargs: Any) -> Any:
            calls["texts"] = texts
            calls["encode_options"] = kwargs
            return [[0.0, 1.0], [1.0, 0.0]]

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeEncoder),
    )
    vectors = generate_embeddings(["first", "second"], model_name="test-model", dimension=2)

    assert calls["model_name"] == "test-model"
    assert calls["truncate_dim"] == 2
    assert calls["texts"] == ["first", "second"]
    assert vectors == [[0.0, 1.0], [1.0, 0.0]]


def test_load_document_skips_existing_content_hash() -> None:
    document = parse_document("company: Acme\n\nRevenue was stable.")
    connection = MagicMock()
    existing_id = uuid4()
    connection.execute.side_effect = [
        MagicMock(fetchone=MagicMock(return_value=None)),
        MagicMock(fetchone=MagicMock(return_value=(existing_id,))),
    ]

    result = load_document(cast(Any, connection), document, (), title="annual-report")

    assert result.document_id == existing_id
    assert result.inserted is False
    assert result.parent_chunks == 0
    assert result.child_chunks == 0
    assert connection.execute.call_count == 2
