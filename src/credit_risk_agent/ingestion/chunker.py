"""Hierarchical parent/child chunking for financial documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from credit_risk_agent.ingestion.parser import Document

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class ChildChunk:
    index: int
    parent_index: int
    content: str
    token_count: int


@dataclass(frozen=True)
class ParentChunk:
    index: int
    content: str
    token_count: int
    children: tuple[ChildChunk, ...]


def _token_spans(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in _TOKEN.finditer(text)]


def _split_to_limit(text: str, max_tokens: int) -> list[str]:
    spans = _token_spans(text)
    if len(spans) <= max_tokens:
        return [text.strip()] if text.strip() else []
    pieces: list[str] = []
    for start in range(0, len(spans), max_tokens):
        first = spans[start][0]
        last = spans[min(start + max_tokens, len(spans)) - 1][1]
        pieces.append(text[first:last].strip())
    return pieces


def _parent_texts(content: str, max_tokens: int) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
    parents: list[str] = []
    current: list[str] = []
    current_count = 0

    for block in blocks:
        block_count = len(_token_spans(block))
        pieces = _split_to_limit(block, max_tokens) if block_count > max_tokens else [block]
        for piece in pieces:
            piece_count = len(_token_spans(piece))
            if current and current_count + piece_count > max_tokens:
                parents.append("\n\n".join(current))
                current = []
                current_count = 0
            current.append(piece)
            current_count += piece_count

    if current:
        parents.append("\n\n".join(current))
    return parents


def _child_chunks(
    content: str,
    parent_index: int,
    first_index: int,
    max_tokens: int,
    overlap_tokens: int,
) -> tuple[ChildChunk, ...]:
    spans = _token_spans(content)
    children: list[ChildChunk] = []
    start = 0
    while start < len(spans):
        end = min(start + max_tokens, len(spans))
        child_content = content[spans[start][0] : spans[end - 1][1]]
        children.append(
            ChildChunk(
                index=first_index + len(children),
                parent_index=parent_index,
                content=child_content,
                token_count=end - start,
            )
        )
        if end == len(spans):
            break
        start = end - overlap_tokens
    return tuple(children)


def chunk_document(
    document: Document,
    *,
    parent_max_tokens: int = 1500,
    child_max_tokens: int = 300,
    overlap_tokens: int = 50,
) -> tuple[ParentChunk, ...]:
    """Chunk a document into context-preserving parents and overlapping children."""
    if parent_max_tokens < 1 or child_max_tokens < 1:
        raise ValueError("Chunk token limits must be positive")
    if overlap_tokens < 0 or overlap_tokens >= child_max_tokens:
        raise ValueError("overlap_tokens must be non-negative and smaller than child_max_tokens")
    if child_max_tokens > parent_max_tokens:
        raise ValueError("child_max_tokens cannot exceed parent_max_tokens")

    parent_texts = _parent_texts(document.content, parent_max_tokens)
    parents: list[ParentChunk] = []
    next_child_index = 0
    for parent_index, content in enumerate(parent_texts):
        children = _child_chunks(
            content,
            parent_index,
            next_child_index,
            child_max_tokens,
            overlap_tokens,
        )
        parents.append(
            ParentChunk(
                index=parent_index,
                content=content,
                token_count=len(_token_spans(content)),
                children=children,
            )
        )
        next_child_index += len(children)
    return tuple(parents)
