from __future__ import annotations

import asyncio
import copy
import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from collections.abc import Sequence
from html.parser import HTMLParser
from typing import Any, ClassVar
from urllib.parse import unquote, urljoin, urlparse

import httpx

from .models import NovelRecord, ReviewSource
from .normalization import clean_text, canonical_url, identity_matches


GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _retry_delay(response, attempt):
    raw = response.headers.get("Retry-After") if response is not None else None
    delay = 0.5 * (2 ** attempt)
    if raw:
        try:
            delay = float(raw)
        except ValueError:
            try:
                date = parsedate_to_datetime(raw)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                delay = (date - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                pass
    return max(0.0, delay) if math.isfinite(delay) and delay <= 5 else None


async def _request_json(client, method, url, *, before_request=None, **kwargs):
    for attempt in range(3):
        if before_request:
            await before_request()
        try:
            response = await client.request(method, url, **kwargs)
        except (httpx.TimeoutException, httpx.NetworkError):
            # A timed-out billable POST may already have spent credits.
            if method != "GET" or attempt == 2:
                raise
            await asyncio.sleep(0.5 * (2 ** attempt))
            continue
        retryable = response.status_code == 429 or (method == "GET" and response.status_code in {500, 502, 503, 504})
        if retryable and attempt < 2:
            delay = _retry_delay(response, attempt)
            if delay is not None:
                await asyncio.sleep(delay)
                continue
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("error"):
            raise ValueError("Expected a successful object response")
        return payload


def _items(payload, key):
    items = payload.get(key, [])
    if not isinstance(items, list):
        raise ValueError("Expected a result list")
    return [item for item in items if isinstance(item, dict)]


class GoogleBooksClient:
    def __init__(self, client: httpx.AsyncClient, api_key: str | None = None) -> None:
        self.client = client
        self.api_key = (os.getenv("GOOGLE_BOOKS_API_KEY", "") if api_key is None else api_key).strip()

    async def search(
        self, title: str, author: str, limit: int = 5, start_index: int = 0
    ) -> tuple[list[NovelRecord], int]:
        query = f"intitle:{title}"
        if author.strip():
            query += f" inauthor:{author}"
        params = {
                "q": query,
                "maxResults": min(max(limit, 1), 40),
                "startIndex": max(start_index, 0),
                "printType": "books",
            }
        if self.api_key:
            params["key"] = self.api_key
        payload = await _request_json(self.client, "GET", GOOGLE_BOOKS_URL, params=params)
        records: list[NovelRecord] = []
        for item in _items(payload, "items"):
            info = item.get("volumeInfo") or {}
            if not isinstance(info, dict):
                continue
            book_title = _clean_text(info.get("title"))
            if not book_title:
                continue
            date = _clean_text(info.get("publishedDate"))
            year = _year_from_date(date)
            links = info.get("imageLinks") or {}
            if not isinstance(links, dict):
                links = {}
            records.append(
                NovelRecord(
                    title=book_title,
                    authors=_as_string_list(info.get("authors")),
                    description=_clean_text(info.get("description")),
                    description_source="google_books" if _clean_text(info.get("description")) else None,
                    publisher=_clean_text(info.get("publisher")),
                    published_year=year,
                    genres=_as_string_list(info.get("categories")),
                    average_rating=_as_float(info.get("averageRating")),
                    ratings_count=_as_int(info.get("ratingsCount")),
                    cover_url=_clean_text(links.get("thumbnail") or links.get("smallThumbnail")),
                    provider="google_books",
                    source_url=_clean_text(info.get("infoLink") or item.get("selfLink")) or "",
                    provider_id=_clean_text(item.get("id")),
                )
            )
        return records, _as_int(payload.get("totalItems")) or 0


class OpenLibraryClient:
    """Open Library adapter with a small in-memory cache and polite request pacing."""

    FIELDS = "key,title,author_name,first_publish_year,publisher,subject,cover_i,ratings_average,ratings_count"
    _shared_cache: ClassVar[
        dict[tuple[str, str, int, int], tuple[float, list[NovelRecord], int]]
    ] = {}
    _shared_request_lock: ClassVar[threading.Lock] = threading.Lock()
    _shared_last_request_at: ClassVar[float] = 0.0

    def __init__(
        self,
        client: httpx.AsyncClient,
        user_agent: str = "NovelMatch/0.1 (educational project)",
        cache_seconds: int = 300,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self.client = client
        self.user_agent = user_agent
        self.cache_seconds = cache_seconds
        self.min_interval_seconds = min_interval_seconds

    async def search(
        self, title: str, author: str, limit: int = 5, offset: int = 0
    ) -> tuple[list[NovelRecord], int]:
        safe_limit = min(max(limit, 1), 100)
        safe_offset = max(offset, 0)
        cache_key = (title.casefold().strip(), author.casefold().strip(), safe_limit, safe_offset)
        cached = self._shared_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_seconds:
            return copy.deepcopy(cached[1]), cached[2]

        params = {
            "q": " ".join(part for part in (title, author) if part.strip()),
            "fields": self.FIELDS,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        payload = await _request_json(self.client, "GET", OPEN_LIBRARY_SEARCH_URL,
                                      params=params, headers={"User-Agent": self.user_agent},
                                      before_request=self._pace)
        records: list[NovelRecord] = []
        for item in _items(payload, "docs"):
            book_title = _clean_text(item.get("title"))
            key = _clean_text(item.get("key"))
            if not book_title or not key:
                continue
            cover_id = _as_int(item.get("cover_i"))
            records.append(
                NovelRecord(
                    title=book_title,
                    authors=_as_string_list(item.get("author_name")),
                    publisher=(_as_string_list(item.get("publisher")) or [None])[0],
                    published_year=_as_int(item.get("first_publish_year")),
                    genres=_as_string_list(item.get("subject"))[:12],
                    average_rating=_as_float(item.get("ratings_average")),
                    ratings_count=_as_int(item.get("ratings_count")),
                    cover_url=f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
                    provider="open_library",
                    source_url=f"https://openlibrary.org{key}",
                    provider_id=key.rsplit("/", 1)[-1],
                )
            )
        total = _as_int(payload.get("numFound")) or 0
        now = time.monotonic()
        for old_key, cached_value in list(self._shared_cache.items()):
            if now - cached_value[0] >= self.cache_seconds:
                self._shared_cache.pop(old_key, None)
        if len(self._shared_cache) >= 256:
            self._shared_cache.pop(next(iter(self._shared_cache)), None)
        self._shared_cache[cache_key] = (now, copy.deepcopy(records), total)
        return records, total

    async def _pace(self):
        # Reserve a slot without tying the lock to a particular event loop.
        with self._shared_request_lock:
            now = time.monotonic()
            slot = max(now, type(self)._shared_last_request_at)
            type(self)._shared_last_request_at = slot + self.min_interval_seconds
        if slot > now:
            await asyncio.sleep(slot - now)


class _StructuredMetadataParser(HTMLParser):
    """Collect only JSON-LD and stable metadata tags from an HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.json_ld: list[Any] = []
        self.meta: dict[str, str] = {}
        self._script_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag.lower() == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._script_parts = []
        elif tag.lower() == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            value = attributes.get("content")
            if key and value:
                self.meta[key] = value

    def handle_data(self, data: str) -> None:
        if self._script_parts is not None:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script_parts is not None:
            raw = "".join(self._script_parts).strip()
            self._script_parts = None
            if not raw:
                return
            try:
                self.json_ld.append(json.loads(raw))
            except (TypeError, ValueError):
                pass


def _goodreads_url(value: str) -> str:
    """Return a canonical HTTPS Goodreads URL, or an empty string."""
    url = canonical_url(value)
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").casefold()
        port = parsed.port
    except ValueError:
        return ""
    if parsed.scheme != "https" or port not in (None, 443):
        return ""
    if hostname != "goodreads.com" and not hostname.endswith(".goodreads.com"):
        return ""
    return url


class GoodreadsClient:
    """Best-effort Goodreads structured-metadata resolver.

    Goodreads HTML is not treated as a stable API. Only structured metadata
    exposed as JSON-LD or recognized meta tags is accepted, and the extracted
    identity is validated by the caller's requested title and author.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def resolve(self, url: str, title: str, author: str) -> NovelRecord | None:
        current = _goodreads_url(url)
        if not current:
            raise ValueError("Goodreads URL must use HTTPS on goodreads.com or a subdomain")

        response = None
        for _ in range(3):
            response = await self.client.get(
                current,
                follow_redirects=False,
                headers={"Accept": "text/html,application/xhtml+xml"},
            )
            if response.status_code not in {301, 302, 303, 307, 308}:
                break
            location = response.headers.get("location")
            redirected = _goodreads_url(urljoin(current, location or ""))
            if not redirected:
                raise ValueError("Goodreads redirect was rejected because it left HTTPS Goodreads")
            current = redirected
        else:
            raise ValueError("Goodreads redirect chain was too long")

        response.raise_for_status()
        parser = _StructuredMetadataParser()
        parser.feed(response.text)
        metadata = _extract_goodreads_metadata(parser, title, author)
        if metadata is None:
            return None

        record = NovelRecord(
            title=metadata["title"],
            authors=metadata["authors"],
            description=metadata.get("description"),
            description_source="goodreads" if metadata.get("description") else None,
            publisher=metadata.get("publisher"),
            published_year=_year_from_date(metadata.get("published_date")),
            genres=metadata.get("genres", []),
            average_rating=_as_float(metadata.get("rating")),
            ratings_count=_as_int(metadata.get("rating_count")),
            cover_url=metadata.get("cover_url"),
            provider="goodreads",
            source_url=current,
        )
        return record if identity_matches(record, title, author) else None


@dataclass
class GoodreadsReviewFetchResult:
    reviews: list[ReviewSource]
    diagnostics: dict[str, Any]


class GoodreadsReviewClient:
    """Fetch only structured review text from an accessible Goodreads page.

    This adapter does not use browser automation, proxying, or anti-bot
    workarounds. Pages without structured review data are treated as
    unavailable rather than guessed from URL text or search snippets.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(
        self, url: str, title: str, author: str, *, limit: int = 8
    ) -> GoodreadsReviewFetchResult:
        current = _goodreads_url(url)
        if not current:
            raise ValueError("Goodreads URL must use HTTPS on goodreads.com or a subdomain")

        response = None
        for _ in range(3):
            response = await self.client.get(
                current,
                follow_redirects=False,
                headers={"Accept": "text/html,application/xhtml+xml"},
            )
            if response.status_code not in {301, 302, 303, 307, 308}:
                break
            redirected = _goodreads_url(urljoin(current, response.headers.get("location", "")))
            if not redirected:
                raise ValueError("Goodreads redirect was rejected because it left HTTPS Goodreads")
            current = redirected
        else:
            raise ValueError("Goodreads redirect chain was too long")

        response.raise_for_status()
        parser = _StructuredMetadataParser()
        parser.feed(response.text)
        books = [book for value in parser.json_ld for book in _book_objects(value)]
        matching_book = next(
            (
                book for book in books
                if (book_title := _clean_text(book.get("name")))
                and (book_authors := _author_names(book.get("author")))
                and identity_matches(NovelRecord(title=book_title, authors=book_authors), title, author)
            ),
            None,
        )
        diagnostics = {
            "fetched": 1,
            "discovered": 0,
            "parsed": 0,
            "rejected": 0,
            "rejection_reasons": {},
        }
        if matching_book is None:
            diagnostics["rejected"] = 1
            diagnostics["rejection_reasons"] = {"identity_mismatch": 1}
            return GoodreadsReviewFetchResult([], diagnostics)

        review_values = matching_book.get("review", [])
        review_values = review_values if isinstance(review_values, list) else [review_values]
        diagnostics["discovered"] = len([item for item in review_values if isinstance(item, dict)])
        candidates: list[ReviewSource] = []
        for item in review_values:
            if not isinstance(item, dict):
                continue
            body = _clean_text(item.get("reviewBody"))
            raw_review_url = _clean_text(item.get("url"))
            review_url = _goodreads_url(urljoin(current, raw_review_url)) if raw_review_url else ""
            if not body or not review_url:
                diagnostics["rejected"] += 1
                reason = "missing_review_text" if not body else "missing_review_url"
                diagnostics["rejection_reasons"][reason] = diagnostics["rejection_reasons"].get(reason, 0) + 1
                continue
            candidates.append(
                ReviewSource(
                    title=_clean_text(matching_book.get("name")) or title,
                    url=review_url,
                    snippet=body,
                    source_name="goodreads.com",
                    evidence_type="review_full_text",
                )
            )
        diagnostics["parsed"] = len(candidates)
        selected = _diverse_review_sample(candidates, min(max(limit, 1), 20))
        diagnostics["rejected"] += max(0, len(candidates) - len(selected))
        if len(candidates) > len(selected):
            diagnostics["rejection_reasons"]["sample_limit"] = len(candidates) - len(selected)
        return GoodreadsReviewFetchResult(selected, diagnostics)


def _diverse_review_sample(records: list[ReviewSource], limit: int) -> list[ReviewSource]:
    buckets: dict[str, list[ReviewSource]] = {"positive": [], "negative": [], "mixed": [], "other": []}
    for record in records:
        buckets[_review_sentiment(record.snippet)].append(record)
    selected: list[ReviewSource] = []
    for bucket in ("positive", "negative", "mixed"):
        if buckets[bucket] and len(selected) < limit:
            selected.append(buckets[bucket].pop(0))
    for record in records:
        if len(selected) >= limit:
            break
        if record not in selected:
            selected.append(record)
    return selected


def _review_sentiment(text: str) -> str:
    normalized_text = text.casefold()
    positive = ("loved", "enjoyed", "excellent", "beautiful", "recommend", "สนุก", "ชอบ")
    negative = ("boring", "slow", "disappointed", "hated", "จากัด", "น่าเบื่อ", "ไม่ชอบ")
    has_positive = any(cue in normalized_text for cue in positive)
    has_negative = any(cue in normalized_text for cue in negative)
    if has_positive and has_negative:
        return "mixed"
    if has_positive:
        return "positive"
    if has_negative:
        return "negative"
    return "other"


def _extract_goodreads_metadata(
    parser: _StructuredMetadataParser, title: str, author: str
) -> dict[str, Any] | None:
    books = []
    for value in parser.json_ld:
        books.extend(_book_objects(value))
    for book in books:
        extracted_title = _clean_text(book.get("name"))
        authors = _author_names(book.get("author"))
        if not extracted_title or not authors:
            continue
        candidate = NovelRecord(title=extracted_title, authors=authors)
        if not identity_matches(candidate, title, author):
            continue
        rating = book.get("aggregateRating") or {}
        return {
            "title": extracted_title,
            "authors": authors,
            "description": _clean_text(book.get("description")),
            "publisher": _publisher_name(book.get("publisher")),
            "published_date": _clean_text(book.get("datePublished")),
            "genres": _as_string_list(book.get("genre")) if isinstance(book.get("genre"), list) else ([book["genre"]] if _clean_text(book.get("genre")) else []),
            "rating": rating.get("ratingValue") if isinstance(rating, dict) else None,
            "rating_count": rating.get("ratingCount") if isinstance(rating, dict) else None,
            "cover_url": _clean_text(book.get("image")),
        }

    title = _clean_text(parser.meta.get("og:title") or parser.meta.get("twitter:title"))
    author = _clean_text(
        parser.meta.get("book:author")
        or parser.meta.get("books:author")
        or parser.meta.get("og:author")
    )
    if not title or not author:
        return None
    return {
        "title": title,
        "authors": [author],
        "description": _clean_text(parser.meta.get("og:description") or parser.meta.get("description")),
        "cover_url": _clean_text(parser.meta.get("og:image")),
    }


def _book_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict) and _is_book(item)]
    if not isinstance(value, dict):
        return []
    graph = value.get("@graph")
    if isinstance(graph, list):
        return [item for item in graph if isinstance(item, dict) and _is_book(item)]
    return [value] if _is_book(value) else []


def _is_book(value: dict[str, Any]) -> bool:
    kind = value.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return any(isinstance(item, str) and item.casefold() == "book" for item in kinds)


def _author_names(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    names = []
    for item in values:
        name = item.get("name") if isinstance(item, dict) else item
        if cleaned := _clean_text(name):
            names.append(cleaned)
    return names


def _publisher_name(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    return _clean_text(value)


class TavilyReviewsClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        include_domains: Sequence[str] = (
            "mebmarket.com",
            "pantip.com",
            "novel.dek-d.com",
            "app.thestorygraph.com",
            "goodreads.com",
        ),
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.include_domains = list(include_domains)

    async def search(self, title: str, author: str, limit: int = 5) -> list[ReviewSource]:
        query = f'book reader reviews "{title}" รีวิว'
        if author.strip():
            query += f' "{author}"'
        payload: dict[str, Any] = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": min(max(limit, 1), 20),
            "include_answer": False,
            "include_raw_content": False,
        }
        if self.include_domains:
            payload["include_domains"] = self.include_domains
            payload["include_domains_mode"] = "restrict"
        payload = await _request_json(self.client, "POST",
            TAVILY_SEARCH_URL,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        results: list[ReviewSource] = []
        for item in _items(payload, "results"):
            url = canonical_url(_clean_text(item.get("url")) or "")
            snippet = _clean_text(item.get("content"))
            if not url or not snippet:
                continue
            hostname = urlparse(url).hostname or ""
            if self.include_domains and not any(hostname == domain or hostname.endswith("." + domain)
                                                for domain in self.include_domains):
                continue
            results.append(
                ReviewSource(
                    title=_clean_text(item.get("title")) or "Untitled source",
                    url=url,
                    snippet=snippet,
                    source_name=hostname.removeprefix("www."),
                    relevance_score=_as_float(item.get("score")),
                    published_date=_clean_text(item.get("published_date")),
                )
            )
        return results


def _clean_text(value: Any) -> str | None:
    return clean_text(value)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _as_int(value: Any) -> int | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        result = int(value)
        return result if result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _as_float(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
