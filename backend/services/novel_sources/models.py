from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceReference:
    provider: str
    url: str
    fields: list[str] = field(default_factory=list)


@dataclass
class NovelRecord:
    title: str
    authors: list[str] = field(default_factory=list)
    description: str | None = None
    description_source: str | None = None
    publisher: str | None = None
    published_year: int | None = None
    genres: list[str] = field(default_factory=list)
    average_rating: float | None = None
    ratings_count: int | None = None
    cover_url: str | None = None
    provider: str = ""
    source_url: str = ""
    provider_id: str | None = None
    match_score: float = 0.0
    sources: list[SourceReference] = field(default_factory=list)


@dataclass
class ReviewSource:
    title: str
    url: str
    snippet: str
    source_name: str | None = None
    relevance_score: float | None = None
    published_date: str | None = None
    review_id: str = ""
    evidence_type: str = "review_excerpt_candidate"
    verification_status: str = "heuristic_only"


@dataclass
class NovelResearchResult:
    query: dict[str, str]
    metadata: NovelRecord | None
    candidates: list[NovelRecord] = field(default_factory=list)
    reviews: list[ReviewSource] = field(default_factory=list)
    sources: list[SourceReference] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pagination: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable data for the Backend API / AI service."""
        return asdict(self)
