import json
from pathlib import Path

import pytest

from credit_risk_agent.cli import main
from credit_risk_agent.config import get_settings
from credit_risk_agent.observability.tracing import Tracer


def test_nested_spans_are_linked_and_flushed(tmp_path: Path) -> None:
    tracer = Tracer(tmp_path, case_id="c1")
    with tracer.span("outer"), tracer.span("inner", tool="demo"):
        pass
    path = tracer.flush()

    records = [json.loads(line) for line in path.read_text().splitlines()]
    outer, inner = records
    assert outer["parent_id"] is None
    assert inner["parent_id"] == outer["span_id"]
    assert inner["attributes"] == {"tool": "demo"}
    assert all(r["status"] == "ok" and r["duration_ms"] is not None for r in records)
    assert all(r["case_id"] == "c1" for r in records)


def test_error_is_recorded_and_reraised(tmp_path: Path) -> None:
    tracer = Tracer(tmp_path)
    with pytest.raises(ValueError), tracer.span("boom"):
        raise ValueError("bad")
    (span,) = tracer.spans
    assert span.status == "error"
    assert "bad" in (span.error or "")


def test_hello_trace_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRA_TRACE_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        assert main(["hello-trace"]) == 0
    finally:
        get_settings.cache_clear()
    assert len(list(tmp_path.glob("*.jsonl"))) == 1
