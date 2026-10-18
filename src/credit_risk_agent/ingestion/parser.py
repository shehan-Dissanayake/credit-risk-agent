"""Parse raw filing text and its lightweight document metadata."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Document:
    content: str
    company: str | None
    doc_type: str
    fiscal_year: int | None
    as_of_date: date | None
    content_hash: str


_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_METADATA_LINE = re.compile(r"^\s*([\w -]+):\s*(.*?)\s*$")
_ALLOWED_DOC_TYPES = {"filing", "transcript", "policy", "news"}


def _metadata_value(metadata: dict[str, str], *names: str) -> str | None:
    normalized = {key.strip().lower().replace(" ", "_"): value for key, value in metadata.items()}
    for name in names:
        value = normalized.get(name)
        if value:
            return value.strip().strip("\"'")
    return None


def _extract_metadata(raw_text: str) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    content = raw_text.lstrip("\ufeff")
    front_matter = _FRONT_MATTER.match(content)
    if front_matter:
        for line in front_matter.group(1).splitlines():
            match = _METADATA_LINE.match(line)
            if match:
                metadata[match.group(1).strip()] = match.group(2).strip()
        content = content[front_matter.end() :]

    lines = content.splitlines()
    while lines and (not lines[0].strip() or _METADATA_LINE.match(lines[0])):
        line = lines.pop(0)
        match = _METADATA_LINE.match(line)
        if match:
            metadata.setdefault(match.group(1).strip(), match.group(2).strip())
    return metadata, "\n".join(lines).strip()


def parse_document(raw_text: str) -> Document:
    """Parse Markdown or plain text, accepting front matter or leading metadata lines."""
    metadata, content = _extract_metadata(raw_text)
    doc_type_value = (_metadata_value(metadata, "doc_type", "document_type") or "filing").lower()
    if doc_type_value not in _ALLOWED_DOC_TYPES:
        doc_type_value = "filing"

    fiscal_year_value = _metadata_value(metadata, "fiscal_year", "year")
    fiscal_year = (
        int(fiscal_year_value) if fiscal_year_value and fiscal_year_value.isdigit() else None
    )

    as_of_date_value = _metadata_value(metadata, "as_of_date", "date")
    as_of_date = date.fromisoformat(as_of_date_value) if as_of_date_value else None
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

    return Document(
        content=normalized_content,
        company=_metadata_value(metadata, "company", "company_name"),
        doc_type=doc_type_value,
        fiscal_year=fiscal_year,
        as_of_date=as_of_date,
        content_hash=content_hash,
    )
