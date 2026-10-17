"""Command line entry point: `cra <command>`."""

import argparse
from pathlib import Path

from credit_risk_agent.config import get_settings
from credit_risk_agent.db import check_database
from credit_risk_agent.migrate import apply_migrations
from credit_risk_agent.observability.tracing import Tracer


def hello_trace() -> Path:
    """Write a tiny two-span trace. Phase 0 smoke test for the tracing skeleton."""
    tracer = Tracer(get_settings().trace_dir, case_id="hello")
    with tracer.span("hello_run", purpose="phase-0 smoke test"), tracer.span("hello_step", step=1):
        pass
    return tracer.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cra", description="Credit risk agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hello-trace", help="Write a sample trace file to verify the setup")
    sub.add_parser("db-check", help="Check database connection and pgvector")
    sub.add_parser("migrate", help="Apply pending SQL migrations from ./migrations")
    args = parser.parse_args(argv)

    if args.command == "hello-trace":
        print(f"Trace written to {hello_trace()}")
    elif args.command == "db-check":
        for key, value in check_database().items():
            print(f"{key}: {value}")
    elif args.command == "migrate":
        applied = apply_migrations()
        print("Applied: " + ", ".join(applied) if applied else "Nothing to apply.")
    return 0
