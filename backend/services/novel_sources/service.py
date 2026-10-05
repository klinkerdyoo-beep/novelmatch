from __future__ import annotations

import asyncio
import copy
import math
import os
from typing import Any

import httpx

from .clients import GoogleBooksClient, OpenLibraryClient, TavilyReviewsClient
from .models import NovelRecord, NovelResearchResult, SourceReference
from .normalization import (canonical_url, clean_text, identity_matches, merge_sources,
                            normalize_reviews, rank_and_merge, record_sources)


class NovelResearchService:
    def __init__(self, *, tavily_api_key: str | None = None,
                 open_library_user_agent: str | None = None,
                 timeout_seconds: float = 12.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.tavily_api_key = (os.getenv("TAVILY_API_KEY", "") if tavily_api_key is None else tavily_api_key).strip()
        self.open_library_user_agent = open_library_user_agent or os.getenv(
            "OPEN_LIBRARY_USER_AGENT", "NovelMatch/0.1 (educational project)")
        self.tavily_review_domains = tuple(domain.strip().lower() for domain in os.getenv(
            "TAVILY_REVIEW_DOMAINS", "mebmarket.com,pantip.com,novel.dek-d.com").split(",") if domain.strip())
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def search(self, title: str, author: str, *,
                     user_provided_description: str | None = None,
                     user_provided_source_url: str | None = None,
                     limit: int = 5, page: int = 1) -> NovelResearchResult:
        title = _required_text(title, "title", 300)
        author = _required_text(author, "author", 300)
        for name, value in (("page", page), ("limit", limit)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        description = None
        if user_provided_description is not None:
            if not isinstance(user_provided_description, str) or len(user_provided_description) > 20000:
                raise ValueError("user_provided_description must be text of at most 20000 characters")
            description = clean_text(user_provided_description)
        user_url = ""
        if user_provided_source_url:
            if not isinstance(user_provided_source_url, str):
                raise ValueError("user_provided_source_url must be an HTTP(S) URL")
            user_url = canonical_url(user_provided_source_url.strip())
            if not user_url:
                raise ValueError("user_provided_source_url must be an HTTP(S) URL")
        limit = min(limit, 40)
        offset = (page - 1) * limit
        warnings = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport,
                                     headers={"User-Agent": self.open_library_user_agent}) as client:
            google = GoogleBooksClient(client)
            library = OpenLibraryClient(client, user_agent=self.open_library_user_agent)
            tavily = TavilyReviewsClient(client, self.tavily_api_key, include_domains=self.tavily_review_domains)
            if self.tavily_api_key:
                google_page, raw_reviews = await asyncio.gather(
                    _safe_call("Google Books", google.search(title, author, limit, offset), warnings, ([], 0)),
                    _safe_call("Tavily", tavily.search(title, author, limit), warnings, []))
            else:
                google_page = await _safe_call("Google Books", google.search(title, author, limit, offset), warnings, ([], 0))
                raw_reviews = []
                warnings.append("Tavily review search skipped: TAVILY_API_KEY is not configured.")
            google_records, google_total = google_page
            google_ranked = rank_and_merge(google_records, title, author)
            primary = next((r for r in google_ranked if identity_matches(r, title, author)), None)
            use_fallback = primary is None or not (primary.description and (primary.genres or primary.published_year))
            library_records, library_total = [], 0
            if use_fallback:
                library_records, library_total = await _safe_call(
                    "Open Library", library.search(title, author, limit, offset), warnings, ([], 0))

        candidates = rank_and_merge([*google_records, *library_records], title, author)
        selected = copy.deepcopy(next((r for r in candidates if identity_matches(r, title, author)), None))
        if selected is None:
            warnings.append("No sufficiently matching title AND author metadata was found on this page.")
            if description:
                selected = NovelRecord(title=title, authors=[author], provider="user_input")
        if selected is not None and description and not selected.description:
            selected.description = description
            selected.description_source = "user_input"
            warnings.append("The description was supplied by the user and has not been independently verified.")
            if user_url:
                selected.sources.append(SourceReference("user_input", user_url, ["description"]))
                if selected.provider == "user_input":
                    selected.source_url = user_url
            else:
                warnings.append("The user-provided description has no source URL.")
        if selected is not None:
            missing = [name for name in ("description", "genres", "published_year", "average_rating", "ratings_count")
                       if getattr(selected, name) in (None, "", [])]
            if missing:
                warnings.append("Missing novel metadata: " + ", ".join(missing) + ".")
        reviews, review_warnings = normalize_reviews(raw_reviews, title, author)
        warnings.extend(review_warnings)
        if not reviews:
            warnings.append("No sufficiently relevant review excerpts passed screening; do not invent reader opinions.")
        sources = record_sources(selected) if selected else []
        if selected and not sources:
            warnings.append("Selected novel metadata has no usable source URL; do not fabricate a citation.")
        sources.extend(SourceReference(r.source_name or "web_search", r.url, ["review_snippet"]) for r in reviews)
        return NovelResearchResult(
            query={"title": title, "author": author}, metadata=selected, candidates=candidates,
            reviews=reviews, sources=merge_sources(sources), warnings=list(dict.fromkeys(warnings)),
            pagination={"page": page, "limit": limit,
                        "google_books": {"total": google_total, "has_more": offset + limit < google_total},
                        "open_library": {"used_as_fallback": use_fallback, "total": library_total,
                                         "has_more": use_fallback and offset + limit < library_total},
                        "reviews": {"limit": min(limit, 20), "has_more": False,
                                    "note": "Tavily reviews are not paginated; changing the metadata page repeats the review search."}})


def _required_text(value, name, max_length):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{name} must contain 1 to {max_length} characters")
    return value.strip()


async def _safe_call(name, awaitable, warnings, default):
    try:
        return await awaitable
    except httpx.TimeoutException:
        warnings.append(f"{name} request timed out.")
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        reason = " Rate limit reached; try again later." if status == 429 else ""
        if status in {401, 403}:
            reason = " Check provider credentials or access permissions."
        if status in {432, 433}:
            reason = " Provider usage limit reached."
        warnings.append(f"{name} returned HTTP {status}.{reason}")
    except httpx.HTTPError:
        warnings.append(f"{name} could not be reached.")
    except (ValueError, TypeError):
        warnings.append(f"{name} returned a response that could not be parsed.")
    return copy.deepcopy(default)


async def search_novel(title: str, author: str, *,
                       user_provided_description: str | None = None,
                       user_provided_source_url: str | None = None,
                       limit: int = 5, page: int = 1) -> dict[str, Any]:
    result = await NovelResearchService().search(
        title, author, user_provided_description=user_provided_description,
        user_provided_source_url=user_provided_source_url, limit=limit, page=page)
    return result.to_dict()
