from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, unquote

from .models import NovelRecord, ReviewSource, SourceReference


def clean_text(value):
    if not isinstance(value, str):
        return None
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(value).split()).strip() or None


def normalized(value: str) -> str:
    # Keep Thai combining marks; \w alone removes meaningful Thai vowels/tones.
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(c for c in value if unicodedata.category(c)[0] in "LNM")


def similarity(left: str, right: str) -> float:
    a, b = normalized(left), normalized(right)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def identity_matches(record: NovelRecord, title: str, author: str) -> bool:
    return similarity(title, record.title) >= 0.88 and any(
        similarity(author, item) >= 0.80 for item in record.authors
    )


def canonical_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username or parsed.password or any(c.isspace() for c in value):
            return ""
        if "{url}" in unquote(parsed.path).lower():
            return ""
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                 if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/",
                           urlencode(sorted(query)), ""))
    except ValueError:
        return ""


def record_sources(record: NovelRecord) -> list[SourceReference]:
    if record.sources:
        return copy.deepcopy(record.sources)
    url = canonical_url(record.source_url)
    if not url:
        return []
    fields = [name for name in ("title", "authors", "publisher", "published_year", "genres",
                               "average_rating", "ratings_count", "cover_url")
              if getattr(record, name) not in (None, "", [])]
    if record.description and record.description_source == record.provider:
        fields.append("description")
    return [SourceReference(record.provider, url, fields)]


def merge_sources(sources: list[SourceReference]) -> list[SourceReference]:
    combined = {}
    for source in sources:
        key = (source.provider, source.url)
        if key not in combined:
            combined[key] = copy.deepcopy(source)
        else:
            combined[key].fields = list(dict.fromkeys(combined[key].fields + source.fields))
    return list(combined.values())


def rank_and_merge(records: list[NovelRecord], title: str, author: str) -> list[NovelRecord]:
    records = copy.deepcopy(records)
    for record in records:
        author_score = max((similarity(author, a) for a in record.authors), default=0.0)
        record.match_score = round(0.7 * similarity(title, record.title) + 0.3 * author_score, 4)
        record.sources = record_sources(record)
    # Prefer a matching Google record; fallback supplements missing fields only.
    records.sort(key=lambda r: (identity_matches(r, title, author),
                               r.provider == "google_books", r.match_score), reverse=True)
    unique = []
    for record in records:
        duplicate = next((r for r in unique
                          if similarity(r.title, record.title) >= 0.94
                          and r.authors and record.authors
                          and max(similarity(a, b) for a in r.authors for b in record.authors) >= 0.94), None)
        if duplicate is None:
            unique.append(record)
            continue
        filled = []
        for name in ("description", "publisher", "published_year", "genres", "cover_url"):
            if getattr(duplicate, name) in (None, "", []) and getattr(record, name) not in (None, "", []):
                setattr(duplicate, name, copy.deepcopy(getattr(record, name)))
                filled.append(name)
                if name == "description":
                    duplicate.description_source = record.description_source
        # Rating and count belong to one provider; never combine incompatible populations.
        if duplicate.average_rating is None and record.average_rating is not None:
            duplicate.average_rating, duplicate.ratings_count = record.average_rating, record.ratings_count
            duplicate.sources = [SourceReference(s.provider, s.url,
                                [f for f in s.fields if f not in {"average_rating", "ratings_count"}])
                                 for s in duplicate.sources]
            filled += ["average_rating", "ratings_count"]
        for source in record.sources:
            fields = [f for f in source.fields if f in filled]
            if fields:
                duplicate.sources.append(SourceReference(source.provider, source.url, fields))
        duplicate.sources = merge_sources(duplicate.sources)
    return unique


def normalize_reviews(records: list[ReviewSource], title: str, author: str, *, return_diagnostics: bool = False):
    """Keep conservative excerpt candidates, not certified reader reviews."""
    accepted, seen_urls, seen_text = [], set(), set()
    rejected = {"invalid_url": 0, "title_mismatch": 0, "wrong_volume": 0,
                "no_opinion_signal": 0, "too_short": 0, "duplicate": 0,
                "author_unconfirmed": 0}
    opinion_cues = ("รีวิว", "อ่านแล้ว", "ชอบ", "ไม่ชอบ", "สนุก", "น่าเบื่อ", "ประทับใจ",
                    "แนะนำ", "เรื่องนี้", "review", "reader review", "enjoyed", "loved",
                    "boring", "pacing", "recommend", "disappointed", "slow", "fast-paced",
                    "beautifully written", "couldn't put down")
    author_unconfirmed = False
    for record in records:
        url = canonical_url(record.url)
        snippet = clean_text(record.snippet) or ""
        url_path = ""
        if url:
            # URL paths can carry a useful title/author slug, while query
            # strings are too ambiguous to use as identity evidence.
            url_path = re.sub(r"[-_/]+", " ", unquote(urlsplit(url).path))
        context = normalized(record.title + " " + url_path + " " + snippet)
        title_key, author_key = normalized(title), normalized(author)
        text_key = normalized(snippet)
        # Require the page heading to identify the exact title. Search snippets
        # often omit the author even when the query included it, so author
        # absence is retained as a limitation rather than an automatic reject.
        # Require the result title to identify the exact title. URL paths and
        # snippets can corroborate author/volume context but are not title
        # identity evidence on their own.
        title_matches = bool(title_key and title_key in normalized(record.title))
        author_matches = bool(author_key and author_key in context)
        volume_pattern = r"(?:ภาค|เล่ม|ตอน|book|volume|vol\.?|part)\s*([0-9๐-๙]+|[ivx]+)\b"
        query_volumes = {m.casefold() for m in re.findall(volume_pattern, title, re.I)}
        page_volumes = {m.casefold() for m in re.findall(volume_pattern, record.title + " " + url_path, re.I)}
        wrong_volume = bool(page_volumes - (query_volumes or {"1", "๑", "i"}))
        opinion = any(cue in snippet.casefold() for cue in opinion_cues)
        if not url:
            rejected["invalid_url"] += 1
            continue
        if not title_matches:
            rejected["title_mismatch"] += 1
            continue
        if wrong_volume:
            rejected["wrong_volume"] += 1
            continue
        if not opinion:
            rejected["no_opinion_signal"] += 1
            continue
        if len(snippet) < 30:
            rejected["too_short"] += 1
            continue
        if url in seen_urls or text_key in seen_text:
            rejected["duplicate"] += 1
            continue
        review = copy.deepcopy(record)
        review.url, review.snippet = url, snippet[:8000]
        review.source_name = (urlsplit(url).hostname or "").removeprefix("www.")
        review.review_id = "review-" + hashlib.sha256(url.encode()).hexdigest()[:16]
        review.evidence_type = "review_excerpt_candidate"
        review.verification_status = "heuristic_only"
        accepted.append(review)
        if not author_matches:
            author_unconfirmed = True
        seen_urls.add(url)
        seen_text.add(text_key)
    warnings = []
    rejected_count = sum(rejected.values())
    if rejected_count:
        reasons = ", ".join(f"{count} {reason.replace('_', ' ')}" for reason, count in rejected.items() if count)
        warnings.append(f"Excluded {rejected_count} review search results ({reasons}).")
    if author_unconfirmed:
        warnings.append("Some review excerpts matched the exact title but did not independently confirm the author.")
    if accepted:
        warnings.append("Review evidence consists of fetched review text or search excerpts screened by title, author and opinion keywords; "
                        "reader authorship has not been verified. Text may be incomplete or promotional.")
    diagnostics = {
        "discovered": len(records),
        "accepted": len(accepted),
        "deduplicated": rejected["duplicate"],
        "rejected": rejected_count,
        "rejection_reasons": {reason: count for reason, count in rejected.items() if count},
    }
    if return_diagnostics:
        return accepted, warnings, diagnostics
    return accepted, warnings
