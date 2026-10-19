import asyncio
import json
from unittest.mock import patch

import httpx

from backend.services.novel_sources.ai_payload import build_ai_payload
from backend.services.novel_sources.clients import GoodreadsReviewClient, _review_sentiment
from backend.services.novel_sources.models import ReviewSource
from backend.services.novel_sources.normalization import normalize_reviews
from backend.services.novel_sources import service as research_service_module
from backend.services.novel_sources.service import NovelResearchService


class _HTMLResponse:
    def __init__(self, html: str, status_code: int = 200):
        self.text = html
        self.status_code = status_code
        self.headers = {"content-type": "text/html"}

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://www.goodreads.com/book/show/1")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("blocked", request=request, response=response)


class _HTMLClient:
    def __init__(self, response):
        self.response = response

    async def get(self, url, **kwargs):
        return self.response


def _goodreads_html(*, title="เพชรพระอุมา", author="พนมเทียน", reviews=None):
    return (
        '<script type="application/ld+json">'
        + json.dumps({
            "@type": "Book",
            "name": title,
            "author": {"@type": "Person", "name": author},
            "review": reviews or [],
        }, ensure_ascii=False)
        + "</script>"
    )


def _review(url, text):
    return {"@type": "Review", "url": url, "reviewBody": text}


def test_exact_title_review_without_author_in_snippet_is_retained():
    candidate = ReviewSource(
        title="The Hobbit Book Review",
        url="https://app.thestorygraph.com/reviews/example",
        snippet=(
            "A reader review of The Hobbit: the adventure is delightful, "
            "and the pacing feels lively throughout the story."
        ),
        source_name="app.thestorygraph.com",
        relevance_score=0.91,
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert len(accepted) == 1
    assert accepted[0].review_id.startswith("review-")
    assert accepted[0].verification_status == "heuristic_only"
    assert any("did not independently confirm the author" in warning for warning in warnings)


def test_review_filter_warning_reports_rejection_reason():
    candidate = ReviewSource(
        title="Another Book Review",
        url="https://app.thestorygraph.com/reviews/example",
        snippet="A reader review with enough text to make the rejection reason clear.",
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert accepted == []
    assert any("1 title mismatch" in warning for warning in warnings)


def test_title_in_result_title_with_author_in_url_is_retained():
    candidate = ReviewSource(
        title="The Hobbit Book Review",
        url="https://goodreads.com/reviews/the-hobbit-j-r-r-tolkien",
        snippet="A reader review: the adventure is delightful and the pacing feels lively throughout.",
        source_name="goodreads.com",
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert len(accepted) == 1
    assert not any("did not independently confirm the author" in warning for warning in warnings)


def test_misleading_title_bearing_url_does_not_admit_unrelated_review():
    candidate = ReviewSource(
        title="Another Book Review",
        url="https://goodreads.com/reviews/the-hobbit-j-r-r-tolkien",
        snippet="A reader review of another book with lively pacing and a strong ending.",
        source_name="goodreads.com",
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert accepted == []
    assert any("1 title mismatch" in warning for warning in warnings)


def test_title_only_in_arbitrary_snippet_is_not_identity_evidence():
    candidate = ReviewSource(
        title="Another Book Review",
        url="https://goodreads.com/reviews/another-book",
        snippet=(
            "This unrelated review mentions The Hobbit and J.R.R. Tolkien, "
            "but discusses a different book and its pacing."
        ),
        source_name="goodreads.com",
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert accepted == []
    assert any("1 title mismatch" in warning for warning in warnings)


def test_wrong_volume_in_url_slug_is_rejected():
    candidate = ReviewSource(
        title="The Hobbit review",
        url="https://goodreads.com/reviews/the-hobbit-volume-2",
        snippet="A review of this book: the pacing is lively and the adventure is enjoyable.",
        source_name="goodreads.com",
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert accepted == []
    assert any("1 wrong volume" in warning for warning in warnings)


def test_goodreads_fetch_preserves_full_diverse_review_text():
    reviews = [
        _review("https://www.goodreads.com/review/show/1", "I loved this novel and recommend it for its vivid adventure and memorable characters."),
        _review("https://www.goodreads.com/review/show/2", "The book was boring and slow, and the middle chapters were difficult to finish."),
        _review("https://www.goodreads.com/review/show/3", "I enjoyed the setting, but the pacing was slow and disappointing in the final chapters."),
    ]
    result = asyncio.run(
        GoodreadsReviewClient(_HTMLClient(_HTMLResponse(_goodreads_html(reviews=reviews)))).fetch(
            "https://www.goodreads.com/book/show/8406756", "เพชรพระอุมา", "พนมเทียน", limit=3
        )
    )

    assert result.diagnostics["fetched"] == 1
    assert result.diagnostics["discovered"] == 3
    assert result.diagnostics["parsed"] == 3
    assert [item.snippet for item in result.reviews] == [item["reviewBody"] for item in reviews]
    assert {"positive", "negative", "mixed"} == {
        _review_sentiment(item.snippet) for item in result.reviews
    }


def test_goodreads_review_identity_mismatch_is_rejected():
    result = asyncio.run(
        GoodreadsReviewClient(
            _HTMLClient(
                _HTMLResponse(
                    _goodreads_html(title="Another Book", author="Another Author", reviews=[
                        _review("https://www.goodreads.com/review/show/1", "I loved this unrelated book and recommend it highly.")
                    ])
                )
            )
        ).fetch("https://www.goodreads.com/book/show/8406756", "เพชรพระอุมา", "พนมเทียน")
    )

    assert result.reviews == []
    assert result.diagnostics["rejection_reasons"] == {"identity_mismatch": 1}


def test_normalization_deduplicates_without_inventing_review_evidence():
    full_text = "I loved this novel and recommend it for its vivid adventure and memorable characters."
    records = [
        ReviewSource(
            title="เพชรพระอุมา", url="https://www.goodreads.com/review/show/1", snippet=full_text,
            source_name="goodreads.com", evidence_type="review_full_text",
        ),
        ReviewSource(
            title="เพชรพระอุมา", url="https://www.goodreads.com/review/show/1",
            snippet="I loved this fabricated replacement, but it must not be selected.",
            source_name="goodreads.com", evidence_type="review_full_text",
        ),
    ]
    accepted, warnings, diagnostics = normalize_reviews(
        records, "เพชรพระอุมา", "พนมเทียน", return_diagnostics=True
    )
    payload = build_ai_payload(
        {"metadata": {"title": "เพชรพระอุมา", "authors": ["พนมเทียน"]}, "reviews": [accepted[0].__dict__]},
        {},
    )

    assert len(accepted) == 1
    assert diagnostics["deduplicated"] == 1
    assert diagnostics["rejected"] == 1
    assert payload["reviews"][0]["text"] == full_text
    assert payload["reviews"][0]["url"] == "https://www.goodreads.com/review/show/1"


class _NoMetadataClient:
    def __init__(self, *args, **kwargs):
        pass

    async def search(self, *args, **kwargs):
        return [], 0


class _BlockedGoodreadsReviews:
    def __init__(self, client):
        pass

    async def fetch(self, *args, **kwargs):
        raise RuntimeError("blocked by source")


class _NoGoodreadsMetadata:
    def __init__(self, client):
        pass

    async def resolve(self, *args, **kwargs):
        return None


class _PantipSearch:
    def __init__(self, client, api_key, include_domains):
        pass

    async def search(self, *args, **kwargs):
        return [ReviewSource(
            title="เพชรพระอุมา review",
            url="https://pantip.com/topic/1",
            snippet="A reader review with enough detail and enjoyable pacing throughout this book.",
            source_name="pantip.com",
        )]


def test_blocked_goodreads_reports_explicit_fallback_status():
    patches = [
        patch.object(research_service_module, "GoogleBooksClient", _NoMetadataClient),
        patch.object(research_service_module, "OpenLibraryClient", _NoMetadataClient),
        patch.object(research_service_module, "TavilyReviewsClient", _PantipSearch),
        patch.object(research_service_module, "GoodreadsClient", _NoGoodreadsMetadata),
        patch.object(research_service_module, "GoodreadsReviewClient", _BlockedGoodreadsReviews),
    ]
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="configured").search(
                "เพชรพระอุมา", "พนมเทียน",
                user_provided_source_url="https://www.goodreads.com/book/show/8406756",
            )
        )

    retrieval = result.pagination["reviews"]["retrieval"]
    assert retrieval["fallback_status"] == "goodreads_failed"
    assert retrieval["source"] == "search_fallback"
    assert result.reviews[0].source_name == "pantip.com"
    assert any("using non-Goodreads search results as fallback" in warning for warning in result.warnings)
