from pathlib import Path

from credit_risk_agent.migrate import discover_migrations


def test_migrations_are_found_in_order(tmp_path: Path) -> None:
    (tmp_path / "0002_b.sql").write_text("select 2;")
    (tmp_path / "0001_a.sql").write_text("select 1;")
    (tmp_path / "notes.txt").write_text("ignored")
    names = [p.name for p in discover_migrations(tmp_path)]
    assert names == ["0001_a.sql", "0002_b.sql"]


def test_repo_migrations_are_numbered() -> None:
    names = [p.name for p in discover_migrations(Path("migrations"))]
    assert names, "no migrations found"
    assert all(n[:4].isdigit() and n[4] == "_" for n in names)
