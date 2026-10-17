"""Minimal structured tracer.

Every run produces one JSONL file: one line per span. The record shape deliberately
mirrors OpenTelemetry/Langfuse concepts (run, span, parent, attributes, status) so we
can export to Langfuse later without changing call sites.

Not thread-safe by design: one Tracer per case/run.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Span:
    name: str
    span_id: str
    parent_id: str | None
    start_time: float
    end_time: float | None = None
    status: str = "ok"
    error: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is None:
            return None
        return round((self.end_time - self.start_time) * 1000, 3)


class Tracer:
    def __init__(self, trace_dir: Path, case_id: str | None = None, run_id: str | None = None):
        self.trace_dir = trace_dir
        self.case_id = case_id
        self.run_id = run_id or uuid.uuid4().hex
        self._spans: list[Span] = []
        self._stack: list[Span] = []

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        parent_id = self._stack[-1].span_id if self._stack else None
        span = Span(
            name=name,
            span_id=uuid.uuid4().hex[:16],
            parent_id=parent_id,
            start_time=time.time(),
            attributes=dict(attributes),
        )
        self._spans.append(span)
        self._stack.append(span)
        try:
            yield span
        except Exception as exc:
            span.status = "error"
            span.error = repr(exc)
            raise
        finally:
            span.end_time = time.time()
            self._stack.pop()

    def flush(self) -> Path:
        """Write all spans to <trace_dir>/<run_id>.jsonl and return the path."""
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        path = self.trace_dir / f"{self.run_id}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for span in self._spans:
                record = {
                    "run_id": self.run_id,
                    "case_id": self.case_id,
                    **asdict(span),
                    "duration_ms": span.duration_ms,
                }
                fh.write(json.dumps(record, default=str) + "\n")
        return path
