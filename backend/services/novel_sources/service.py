from __future__ import annotations

import asyncio
import copy
import math
import os
from typing import Any

import httpx

from .clients import (GoodreadsClient, GoodreadsReviewClient, GoogleBooksClient,
                      OpenLibraryClient, TavilyReviewsClient, _goodreads_url)
from .models import NovelRecord, NovelResearchResult, SourceReference
from .normalization import (canonical_url, clean_text, identity_matches, merge_sources,
                            normalize_reviews, rank_and_merge, record_sources)

DEFAULT_TAVILY_REVIEW_DOMAINS = (
    "mebmarket.com",
    "pantip.com",
    "novel.dek-d.com",
    "app.thestorygraph.com",
    "goodreads.com",
)


class NovelResearchService:
    def __init__(self, *, tavily_api_key: str | None = None,
                 open_library_user_agent: str | None = None,
                 timeout_seconds: float = 12.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.tavily_api_key = (os.getenv("TAVILY_API_KEY", "") if tavily_api_key is None else tavily_api_key).strip()
        self.open_library_user_agent = open_library_user_agent or os.getenv(
            "OPEN_LIBRARY_USER_AGENT", "NovelMatch/0.1 (educational project)")
        configured_domains = tuple(
            domain.strip().lower()
            for domain in os.getenv("TAVILY_REVIEW_DOMAINS", "").split(",")
            if domain.strip()
        )
        self.tavily_review_domains = tuple(dict.fromkeys(
            (*DEFAULT_TAVILY_REVIEW_DOMAINS, *configured_domains)
        ))
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
            goodreads = GoodreadsClient(client)
            goodreads_reviews = GoodreadsReviewClient(client)
            if self.tavily_api_key:
                google_page, raw_reviews = await asyncio.gather(
                    _safe_call("Google Books", google.search(title, author, limit, offset), warnings, ([], 0)),
                    _safe_call("Tavily", tavily.search(title, author, max(limit, 10)), warnings, []))
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

            goodreads_records = []
            goodreads_attempted = False
            primary_candidates = rank_and_merge([*google_records, *library_records], title, author)
            primary_selected = next(
                (r for r in primary_candidates if identity_matches(r, title, author)),
                None,
            )
            if _needs_metadata_fallback(primary_selected):
                goodreads_urls = []
                for candidate_url in [user_url, *(review.url for review in raw_reviews)]:
                    candidate_url = _goodreads_url(candidate_url)
                    if candidate_url and candidate_url not in goodreads_urls:
                        goodreads_urls.append(candidate_url)
                for candidate_url in goodreads_urls:
                    goodreads_attempted = True
                    record = await _safe_call(
                        "Goodreads", goodreads.resolve(candidate_url, title, author), warnings, None)
                    if record is not None:
                        goodreads_records.append(record)
                        break
                if goodreads_attempted and not goodreads_records:
                    warnings.append(
                        "Goodreads metadata fallback did not produce verified matching metadata."
                    )

            goodreads_review_url = _goodreads_url(user_url)
            if not goodreads_review_url:
                goodreads_review_url = next(
                    (_goodreads_url(review.url) for review in raw_reviews if _goodreads_url(review.url)),
                    "",
                )
            review_candidates = raw_reviews
            review_retrieval = {
                "source": "search_fallback",
                "fallback_status": "not_attempted",
                "discovered": len(raw_reviews),
                "fetched": 0,
                "parsed": len(raw_reviews),
                "accepted": 0,
                "deduplicated": 0,
                "rejected": 0,
                "rejection_reasons": {},
            }
            if goodreads_review_url:
                try:
                    fetched_reviews = await goodreads_reviews.fetch(
                        goodreads_review_url,
                        title,
                        author,
                        limit=min(max(limit, 4), 20),
                    )
                    review_retrieval.update(fetched_reviews.diagnostics)
                    review_retrieval["discovered"] += len(raw_reviews)
                    if fetched_reviews.reviews:
                        review_candidates = fetched_reviews.reviews
                        review_retrieval["source"] = "goodreads"
                        review_retrieval["fallback_status"] = "not_needed"
                    else:
                        review_candidates = [r for r in raw_reviews if not _goodreads_url(r.url)]
                        review_retrieval["source"] = "search_fallback"
                        review_retrieval["fallback_status"] = "goodreads_empty"
                        review_retrieval["parsed"] = len(review_candidates)
                        warnings.append("Goodreads reviews were unavailable or had no verified full text; using non-Goodreads search results as fallback.")
                except Exception as exc:
                    review_candidates = [r for r in raw_reviews if not _goodreads_url(r.url)]
                    review_retrieval["source"] = "search_fallback"
                    review_retrieval["fallback_status"] = "goodreads_failed"
                    review_retrieval["parsed"] = len(review_candidates)
                    warnings.append(f"Goodreads review retrieval failed; using non-Goodreads search results as fallback ({type(exc).__name__}).")

        candidates = rank_and_merge(
            [*google_records, *library_records, *goodreads_records], title, author)
        selected = copy.deepcopy(next((r for r in candidates if identity_matches(r, title, author)), None))
        if selected is None:
            warnings.append("No sufficiently matching title AND author metadata was found on this page.")
            if description:
                selected = NovelRecord(title=title, authors=[author], provider="user_input")
        _apply_user_description(selected, description, user_url, warnings)
        if selected is not None:
            missing = [name for name in ("description", "publisher", "genres", "published_year", "average_rating", "ratings_count")
                       if getattr(selected, name) in (None, "", [])]
            if missing:
                warnings.append("Missing novel metadata: " + ", ".join(missing) + ".")
        reviews, review_warnings, normalized_diagnostics = normalize_reviews(
            review_candidates, title, author, return_diagnostics=True)
        review_retrieval["accepted"] = normalized_diagnostics["accepted"]
        review_retrieval["deduplicated"] = normalized_diagnostics["deduplicated"]
        review_retrieval["rejected"] += normalized_diagnostics["rejected"]
        for reason, count in normalized_diagnostics["rejection_reasons"].items():
            review_retrieval["rejection_reasons"][reason] = review_retrieval["rejection_reasons"].get(reason, 0) + count
        warnings.extend(review_warnings)
        if not reviews:
            warnings.append("No sufficiently relevant review excerpts passed screening; do not invent reader opinions.")
        sources = record_sources(selected) if selected else []
        if selected and not sources:
            warnings.append("Selected novel metadata has no usable source URL; do not fabricate a citation.")
        sources.extend(
            SourceReference(
                r.source_name or "web_search",
                r.url,
                ["review_full_text" if r.evidence_type == "review_full_text" else "review_snippet"],
            )
            for r in reviews
        )
        return NovelResearchResult(
            query={"title": title, "author": author}, metadata=selected, candidates=candidates,
            reviews=reviews, sources=merge_sources(sources), warnings=list(dict.fromkeys(warnings)),
            pagination={"page": page, "limit": limit,
                        "google_books": {"total": google_total, "has_more": offset + limit < google_total},
                        "open_library": {"used_as_fallback": use_fallback, "total": library_total,
                                         "has_more": use_fallback and offset + limit < library_total},
                        "reviews": {"limit": min(max(limit, 10), 20), "has_more": False,
                                    "retrieval": review_retrieval,
                                    "note": "Review retrieval is bounded; changing the metadata page repeats the review search."}})


def _required_text(value, name, max_length):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{name} must contain 1 to {max_length} characters")
    return value.strip()


def _needs_metadata_fallback(record: NovelRecord | None) -> bool:
    return record is None or not (record.description and (record.genres or record.published_year))


def _apply_user_description(
    selected: NovelRecord | None,
    description: str | None,
    user_url: str,
    warnings: list[str],
) -> None:
    """Fill only missing descriptions after provider identity is selected."""
    if selected is None or not description or selected.description:
        return
    selected.description = description
    selected.description_source = "user_input"
    warnings.append("The description was supplied by the user and has not been independently verified.")
    if user_url:
        selected.sources.append(SourceReference("user_input", user_url, ["description"]))
        if selected.provider == "user_input":
            selected.source_url = user_url
    else:
        warnings.append("The user-provided description has no source URL.")


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
