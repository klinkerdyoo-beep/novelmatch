import asyncio
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


# backend/main.py is run from the backend directory in production. Make that
# import layout explicit here while keeping the database out of this unit test.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("database", types.SimpleNamespace(engine=object()))

import main  # noqa: E402

from services.gemini_service import (  # noqa: E402
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from services.novel_sources.models import NovelRecord  # noqa: E402
from services.novel_sources.clients import GoodreadsClient  # noqa: E402
from services.novel_sources.service import NovelResearchService  # noqa: E402
from services.novel_sources.user_input import normalize_user_input  # noqa: E402
from services.novel_sources import service as research_service_module  # noqa: E402


class AnalysisEndpointTests(unittest.TestCase):
    def test_gemini_503_uses_configured_gpt_oss_fallback(self):
        request = main.AnalysisRequest(
            title="A Novel",
            author="An Author",
            user_preference={"liked_genres": ["Fantasy"]},
        )
        payload = {"user_preference": {}, "novel": {}, "reviews": []}
        expected = types.SimpleNamespace(model_dump=lambda: {"match_score": 75})

        with patch.dict(os.environ, {
            "GPT_OSS_BASE_URL": "https://nvidia.example/v1",
            "GPT_OSS_API_KEY": "test-key",
            "GPT_OSS_MODEL": "openai/gpt-oss-20b",
        }), \
                patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=object())), \
                patch.object(main, "build_ai_payload", return_value=payload), \
                patch.object(main.GeminiAIService, "analyze", side_effect=GeminiUnavailableError("Gemini 503")), \
                patch.object(main, "_analyze_with_gpt_oss", return_value=expected) as fallback, \
                patch.object(main, "validate_analysis_evidence"), \
                patch.object(main, "merge_analysis_limitations", return_value={"match_score": 75}):
            result = asyncio.run(main.analyze_novel(request))

        fallback.assert_called_once_with(payload)
        self.assertEqual(result, {"match_score": 75})

    def test_gemini_rate_limit_and_timeout_are_transient_fallback_errors(self):
        for transient_error in (GeminiRateLimitError("Gemini 429"), GeminiTimeoutError("Gemini timeout")):
            request = main.AnalysisRequest(
                title="A Novel",
                author="An Author",
                user_preference={"liked_genres": ["Fantasy"]},
            )
            payload = {"user_preference": {}, "novel": {}, "reviews": []}
            expected = types.SimpleNamespace(model_dump=lambda: {"match_score": 75})

            with self.subTest(error=type(transient_error).__name__), patch.dict(os.environ, {
                "GPT_OSS_BASE_URL": "https://nvidia.example/v1",
                "GPT_OSS_API_KEY": "test-key",
                "GPT_OSS_MODEL": "openai/gpt-oss-20b",
            }), patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=object())), \
                    patch.object(main, "build_ai_payload", return_value=payload), \
                    patch.object(main.GeminiAIService, "analyze", side_effect=transient_error), \
                    patch.object(main, "_analyze_with_gpt_oss", return_value=expected) as fallback, \
                    patch.object(main, "validate_analysis_evidence"), \
                    patch.object(main, "merge_analysis_limitations", return_value={"match_score": 75}):
                result = asyncio.run(main.analyze_novel(request))

            fallback.assert_called_once_with(payload)
            self.assertEqual(result, {"match_score": 75})

    def test_gemini_transient_error_without_gpt_oss_configuration_keeps_http_error(self):
        request = main.AnalysisRequest(
            title="A Novel",
            author="An Author",
            user_preference={"liked_genres": ["Fantasy"]},
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), \
                patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=object())), \
                patch.object(main, "build_ai_payload", return_value={"user_preference": {}, "novel": {}, "reviews": []}), \
                patch.object(main.GeminiAIService, "analyze", side_effect=GeminiUnavailableError("Gemini 503")), \
                patch.object(main, "_analyze_with_gpt_oss") as fallback:
            with self.assertRaises(main.HTTPException) as raised:
                asyncio.run(main.analyze_novel(request))

        fallback.assert_not_called()
        self.assertEqual(raised.exception.status_code, 502)

    def test_pipeline_is_called_and_validated_output_is_returned(self):
        request = main.AnalysisRequest(
            title="A Novel",
            author="An Author",
            user_preference={"liked_genres": ["Fantasy"]},
        )
        research = object()
        payload = {
            "user_preference": request.user_preference,
            "novel": {"title": "A Novel"},
            "reviews": [],
        }
        analysis = types.SimpleNamespace(model_dump=lambda: {"match_score": None})

        with patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=research)) as search, \
                patch.object(main, "build_ai_payload", return_value=payload) as build_payload, \
                patch.object(main.GeminiAIService, "analyze", return_value=analysis) as analyze, \
                patch.object(main, "validate_analysis_evidence") as validate, \
                patch.object(main, "merge_analysis_limitations", return_value={"match_score": None}) as merge:
            result = asyncio.run(main.analyze_novel(request))

        search.assert_awaited_once()
        build_payload.assert_called_once_with(research, request.user_preference)
        analyze.assert_called_once_with(**payload)
        validate.assert_called_once_with({"match_score": None}, payload)
        merge.assert_called_once_with({"match_score": None}, payload)
        self.assertEqual(result, {"match_score": None})

    def test_nested_teammate_form_is_normalized_once_before_pipeline(self):
        request = main.AnalysisRequest(
            target_novel={"title": "A Novel", "author": "An Author", "synopsis": "Synopsis"},
            user_preferences={
                "genre_preferences": {"liked_genres": ["Fantasy"]},
                "character_preferences": {"liked_traits": ["Kind"]},
                "story_element_preferences": {"liked_elements": ["Fast-paced"]},
            },
        )
        research = object()
        payload = {"user_preference": {"liked_genres": ["Fantasy"]}, "novel": {}, "reviews": []}
        analysis = types.SimpleNamespace(model_dump=lambda: {"match_score": None})

        with patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=research)) as search, \
                patch.object(main, "build_ai_payload", return_value=payload) as build_payload, \
                patch.object(main.GeminiAIService, "analyze", return_value=analysis), \
                patch.object(main, "validate_analysis_evidence"), \
                patch.object(main, "merge_analysis_limitations", return_value={"match_score": None}):
            result = asyncio.run(main.analyze_novel(request))

        search.assert_awaited_once_with(
            "A Novel",
            "An Author",
            user_provided_description="Synopsis",
            user_provided_source_url=None,
        )
        normalized = build_payload.call_args.args[1]
        self.assertEqual(normalized["character_preferences"], ["Likes: Kind"])
        self.assertEqual(normalized["story_preferences"], ["Likes: Fast-paced"])
        self.assertEqual(normalized["rated_novels"], [])
        self.assertEqual(result, {"match_score": None})

    def test_gpt_oss_provider_uses_same_validated_pipeline(self):
        request = main.AnalysisRequest(
            title="A Novel",
            author="An Author",
            user_preference={"liked_genres": ["Fantasy"]},
            provider="gpt_oss",
        )
        payload = {
            "user_preference": request.user_preference,
            "novel": {"title": "A Novel"},
            "reviews": [],
        }
        analysis = types.SimpleNamespace(
            model_dump=lambda: {"match_score": None},
        )

        with patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=object())), \
                patch.object(main, "build_ai_payload", return_value=payload), \
                patch.object(main, "_analyze_with_gpt_oss", return_value=analysis) as analyze, \
                patch.object(main, "validate_analysis_evidence"), \
                patch.object(main, "merge_analysis_limitations", return_value={"match_score": None}):
            result = asyncio.run(main.analyze_novel(request))

        analyze.assert_called_once_with(payload)
        self.assertEqual(result, {"match_score": None})

    def test_gpt_oss_request_uses_shared_prompt_schema_and_parses_response(self):
        payload = {"user_preference": {}, "novel": {}, "reviews": []}
        response_json = json.dumps({
            "match_score": None,
            "match_level": None,
            "matches": [],
            "mismatches": [],
            "review_summary": {"positive": [], "negative": [], "mixed": []},
            "sources": [],
            "limitations": [],
        })
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=response_json))]
                )

        class FakeOpenAI:
            def __init__(self, **kwargs):
                self.chat = types.SimpleNamespace(completions=FakeCompletions())

        with patch.dict(os.environ, {
            "GPT_OSS_BASE_URL": "https://nvidia.example/v1",
            "GPT_OSS_API_KEY": "test-key",
            "GPT_OSS_MODEL": "openai/gpt-oss-20b",
        }), patch.object(main, "OpenAI", FakeOpenAI):
            result = main._analyze_with_gpt_oss(payload)

        self.assertIsNone(result.match_score)
        self.assertEqual(captured["model"], "openai/gpt-oss-20b")
        self.assertEqual(captured["extra_body"]["guided_json"], main.MatchAnalysis.model_json_schema())
        self.assertTrue(captured["messages"][0]["content"].startswith(main.MASTER_ANALYSIS_PROMPT))
        self.assertIn("match_score as an integer from 0 to 100", captured["messages"][0]["content"])
        self.assertIn(json.dumps(payload, ensure_ascii=False), captured["messages"][1]["content"])

    def test_gpt_oss_timeout_is_safe(self):
        class TimeoutCompletions:
            def create(self, **kwargs):
                raise TimeoutError("read timed out")

        class TimeoutOpenAI:
            def __init__(self, **kwargs):
                self.chat = types.SimpleNamespace(completions=TimeoutCompletions())

        with patch.dict(os.environ, {
            "GPT_OSS_BASE_URL": "https://nvidia.example/v1",
            "GPT_OSS_API_KEY": "test-key",
            "GPT_OSS_MODEL": "openai/gpt-oss-20b",
        }), patch.object(main, "OpenAI", TimeoutOpenAI):
            with self.assertRaises(main.GPTOSSTimeoutError):
                main._analyze_with_gpt_oss({"user_preference": {}, "novel": {}, "reviews": []})

    def test_configuration_errors_are_exposed_as_service_unavailable(self):
        request = main.AnalysisRequest(
            title="A Novel",
            author="An Author",
            user_preference={},
        )
        with patch.object(main.NovelResearchService, "search", new=AsyncMock(return_value=object())), \
                patch.object(main, "build_ai_payload", return_value={}), \
                patch.object(main.GeminiAIService, "analyze", side_effect=GeminiConfigurationError("missing key")):
            with self.assertRaises(main.HTTPException) as raised:
                asyncio.run(main.analyze_novel(request))

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "missing key")


class _FakeGoogleBooksClient:
    record = None

    def __init__(self, client):
        pass

    async def search(self, title, author, limit, start_index):
        return ([self.record] if self.record else [], 1 if self.record else 0)


class _FakeOpenLibraryClient:
    record = None

    def __init__(self, client, user_agent):
        pass

    async def search(self, title, author, limit, offset):
        return ([self.record] if self.record else [], 1 if self.record else 0)


class _FakeGoodreadsClient:
    record = None
    calls = 0

    def __init__(self, client):
        pass

    async def resolve(self, url, title, author):
        type(self).calls += 1
        return self.record


def _research_record(*, description):
    return NovelRecord(
        title="The Verdict",
        authors=["Chat Kobchitti"],
        description=description,
        description_source="google_books" if description else None,
        genres=["Literary fiction"],
        provider="google_books",
        source_url="https://books.example/the-verdict",
    )


def _patch_research_clients(google_record, open_library_record=None, goodreads_record=None):
    _FakeGoogleBooksClient.record = google_record
    _FakeOpenLibraryClient.record = open_library_record
    _FakeGoodreadsClient.record = goodreads_record
    _FakeGoodreadsClient.calls = 0
    return patch.object(
        research_service_module,
        "GoogleBooksClient",
        _FakeGoogleBooksClient,
    ), patch.object(
        research_service_module,
        "OpenLibraryClient",
        _FakeOpenLibraryClient,
    ), patch.object(
        research_service_module,
        "GoodreadsClient",
        _FakeGoodreadsClient,
    )


def test_provider_identity_is_independent_of_incorrect_user_synopsis():
    patches = _patch_research_clients(_research_record(description="Provider description."))
    with patches[0], patches[1], patches[2]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="").search(
                "The Verdict",
                "Chat Kobchitti",
                user_provided_description="Incorrect user synopsis.",
            )
        )

    assert result.metadata.provider == "google_books"
    assert result.metadata.description == "Provider description."
    assert result.metadata.description_source == "google_books"
    assert all("not been independently verified" not in warning for warning in result.warnings)


def test_user_synopsis_is_marked_unverified_when_provider_description_is_missing():
    patches = _patch_research_clients(_research_record(description=None))
    with patches[0], patches[1], patches[2]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="").search(
                "The Verdict",
                "Chat Kobchitti",
                user_provided_description="User supplied synopsis.",
                user_provided_source_url="https://www.goodreads.com/book/show/8406756",
            )
        )

    assert result.metadata.provider == "google_books"
    assert result.metadata.description == "User supplied synopsis."
    assert result.metadata.description_source == "user_input"
    assert any("not been independently verified" in warning for warning in result.warnings)
    assert any(source.url == "https://www.goodreads.com/book/show/8406756" for source in result.sources)


def test_complete_google_metadata_prevents_provider_fallbacks():
    patches = _patch_research_clients(_research_record(description="Provider description."))
    with patches[0], patches[1], patches[2]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="").search("The Verdict", "Chat Kobchitti")
        )

    assert result.metadata.provider == "google_books"
    assert _FakeGoodreadsClient.calls == 0


def test_incomplete_google_metadata_is_supplemented_by_open_library():
    open_library_record = NovelRecord(
        title="The Verdict",
        authors=["Chat Kobchitti"],
        description="Open Library description.",
        description_source="open_library",
        publisher="Open Library Press",
        published_year=2020,
        genres=["Literary fiction"],
        provider="open_library",
        source_url="https://openlibrary.org/works/OL1W",
    )
    patches = _patch_research_clients(
        _research_record(description=None), open_library_record=open_library_record
    )
    with patches[0], patches[1], patches[2]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="").search("The Verdict", "Chat Kobchitti")
        )

    assert result.metadata.description == "Open Library description."
    assert result.metadata.publisher == "Open Library Press"
    assert result.metadata.published_year == 2020
    assert _FakeGoodreadsClient.calls == 0


def test_complete_open_library_metadata_is_not_replaced_by_sparse_goodreads():
    open_library_record = NovelRecord(
        title="The Verdict",
        authors=["Chat Kobchitti"],
        description="Open Library description.",
        description_source="open_library",
        publisher="Open Library Press",
        published_year=2020,
        genres=["Literary fiction"],
        provider="open_library",
        source_url="https://openlibrary.org/works/OL1W",
    )
    sparse_goodreads = NovelRecord(
        title="The Verdict",
        authors=["Chat Kobchitti"],
        provider="goodreads",
        source_url="https://www.goodreads.com/book/show/8406756",
    )
    patches = _patch_research_clients(
        None, open_library_record=open_library_record, goodreads_record=sparse_goodreads
    )
    with patches[0], patches[1], patches[2]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="").search(
                "The Verdict",
                "Chat Kobchitti",
                user_provided_source_url="https://www.goodreads.com/book/show/8406756",
            )
        )

    assert result.metadata.provider == "open_library"
    assert result.metadata.description == "Open Library description."
    assert _FakeGoodreadsClient.calls == 0


class _FakeHTMLResponse:
    def __init__(self, html, status_code=200, headers=None):
        self.text = html
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("unexpected HTTP error")


class _FakeHTMLClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_goodreads_structured_metadata_requires_matching_identity():
    client = _FakeHTMLClient(
        _FakeHTMLResponse(
            '<script type="application/ld+json">'
            '{"@type":"Book","name":"The Verdict",'
            '"author":{"@type":"Person","name":"Chat Kobchitti"},'
            '"description":"A verified description.","genre":["Literary fiction"]}'
            "</script>"
        )
    )

    result = asyncio.run(
        GoodreadsClient(client).resolve(
            "https://www.goodreads.com/book/show/8406756",
            "The Verdict",
            "Chat Kobchitti",
        )
    )

    assert result.provider == "goodreads"
    assert result.title == "The Verdict"
    assert result.authors == ["Chat Kobchitti"]
    assert result.source_url == "https://www.goodreads.com/book/show/8406756"


def test_goodreads_structured_metadata_rejects_mismatched_identity():
    client = _FakeHTMLClient(
        _FakeHTMLResponse(
            '<script type="application/ld+json">'
            '{"@type":"Book","name":"Another Book",'
            '"author":{"@type":"Person","name":"Another Author"}}'
            "</script>"
        )
    )

    result = asyncio.run(
        GoodreadsClient(client).resolve(
            "https://www.goodreads.com/book/show/8406756",
            "The Verdict",
            "Chat Kobchitti",
        )
    )

    assert result is None


def test_goodreads_skips_unrelated_json_ld_book_and_accepts_matching_book():
    client = _FakeHTMLClient(
        _FakeHTMLResponse(
            '<script type="application/ld+json">'
            '[{"@type":"Book","name":"Another Book",'
            '"author":{"@type":"Person","name":"Another Author"}},'
            '{"@type":"Book","name":"The Verdict",'
            '"author":{"@type":"Person","name":"Chat Kobchitti"}}]'
            "</script>"
        )
    )

    result = asyncio.run(
        GoodreadsClient(client).resolve(
            "https://www.goodreads.com/book/show/8406756",
            "The Verdict",
            "Chat Kobchitti",
        )
    )

    assert result is not None
    assert result.title == "The Verdict"


def test_goodreads_rejects_non_goodreads_redirect():
    client = _FakeHTMLClient(
        _FakeHTMLResponse(
            "",
            status_code=302,
            headers={"location": "https://example.com/book"},
        )
    )

    with pytest.raises(ValueError, match="redirect was rejected"):
        asyncio.run(
            GoodreadsClient(client).resolve(
                "https://www.goodreads.com/book/show/8406756",
                "The Verdict",
                "Chat Kobchitti",
            )
        )

    assert len(client.calls) == 1


def test_goodreads_is_only_attempted_when_primary_metadata_is_incomplete():
    goodreads_record = NovelRecord(
        title="The Verdict",
        authors=["Chat Kobchitti"],
        description="Goodreads description.",
        description_source="goodreads",
        genres=["Literary fiction"],
        provider="goodreads",
        source_url="https://www.goodreads.com/book/show/8406756",
    )
    patches = _patch_research_clients(
        _research_record(description=None),
        goodreads_record=goodreads_record,
    )
    with patches[0], patches[1], patches[2]:
        result = asyncio.run(
            NovelResearchService(tavily_api_key="").search(
                "The Verdict",
                "Chat Kobchitti",
                user_provided_source_url="https://www.goodreads.com/book/show/8406756",
            )
        )

    assert result.metadata.provider == "google_books"
    assert result.metadata.description == "Goodreads description."
    assert result.metadata.source_url == "https://books.example/the-verdict"
    assert _FakeGoodreadsClient.calls == 1


def test_nested_source_url_is_preserved_for_research():
    target, _ = normalize_user_input(
        {
            "target_novel": {
                "title": "The Verdict",
                "author": "Chat Kobchitti",
                "synopsis": "A synopsis.",
                "source_url": "https://www.goodreads.com/book/show/8406756",
            },
            "user_preferences": {},
        }
    )

    assert target["source_url"] == "https://www.goodreads.com/book/show/8406756"


if __name__ == "__main__":
    unittest.main()
