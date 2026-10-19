import asyncio
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


# backend/main.py is run from the backend directory in production. Make that
# import layout explicit here while keeping the database out of this unit test.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("database", types.SimpleNamespace(engine=object()))

import main  # noqa: E402
from services.gemini_service import (  # noqa: E402
    GeminiConfigurationError,
    GeminiUnavailableError,
)


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
        self.assertEqual(captured["messages"][0]["content"], main.MASTER_ANALYSIS_PROMPT)
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


if __name__ == "__main__":
    unittest.main()
