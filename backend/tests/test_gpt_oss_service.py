import json
from unittest.mock import Mock, patch

import httpx
import pytest
from openai import APITimeoutError

from backend.services.gpt_oss_service import (
    GPTOSSConfigurationError,
    GPTOSSInvalidResponseError,
    GPTOSSRateLimitError,
    GPTOSSService,
    GPTOSSTimeoutError,
)
from backend.tests.test_gemini_service import INPUT_PAYLOAD, REVIEW, valid_response
from backend.services.gemini_service import MatchAnalysis
from backend.services.novel_sources.ai_payload import (
    InsufficientNovelDataError,
    build_ai_payload,
)


class TestGPTOSSService:
    def _client(self, content: str) -> Mock:
        client = Mock()
        client.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content=content))
        ]
        return client

    def test_valid_mocked_response_uses_shared_prompt_and_schema(self):
        client = self._client(valid_response())
        service = GPTOSSService(client=client, model="openai/gpt-oss-20b")

        result = service.analyze(**INPUT_PAYLOAD)

        assert result.match_level == "High"
        request = client.chat.completions.create.call_args.kwargs
        assert request["model"] == "openai/gpt-oss-20b"
        assert request["messages"][0]["role"] == "system"
        assert "Novel Compatibility Analyzer" in request["messages"][0]["content"]
        assert "match_score as an integer from 0 to 100" in request["messages"][0]["content"]
        user_message = request["messages"][1]["content"]
        assert json.loads(user_message.split("\n\n", 1)[1]) == INPUT_PAYLOAD
        assert request["extra_body"] == {"guided_json": MatchAnalysis.model_json_schema()}

    @pytest.mark.parametrize(
        ("score", "expected"),
        [(77.4, 77), (77.5, 78), (77, 77), (None, None)],
    )
    def test_score_normalization_preserves_response_contract(self, score, expected):
        client = self._client(
            valid_response(
                match_score=score,
                match_level=None if score is None else "Medium",
            )
        )

        result = GPTOSSService(client=client, model="test-model").analyze(**INPUT_PAYLOAD)

        assert result.match_score == expected

    @pytest.mark.parametrize(
        "score",
        [100.1, -0.1, "77.4", True, float("inf"), float("nan")],
    )
    def test_invalid_scores_are_rejected_without_clamping(self, score):
        client = self._client(valid_response(match_score=score))

        with pytest.raises(GPTOSSInvalidResponseError):
            GPTOSSService(client=client, model="test-model").analyze(**INPUT_PAYLOAD)

    def test_empty_reviews_can_return_unknown_score_without_evidence(self):
        client = self._client(
            valid_response(
                match_score=None,
                match_level=None,
                matches=[],
                mismatches=[],
                review_summary={"positive": [], "negative": [], "mixed": []},
                sources=[],
                limitations=["Reader reviews were not provided."],
            )
        )
        service = GPTOSSService(client=client, model="test-model")

        result = service.analyze(
            user_preference=INPUT_PAYLOAD["user_preference"],
            novel=INPUT_PAYLOAD["novel"],
            reviews=[],
        )

        assert result.match_score is None
        assert result.match_level is None
        assert result.sources == []
        assert result.limitations == ["Reader reviews were not provided."]

    @pytest.mark.parametrize(
        ("exception", "expected"),
        [
            (TimeoutError("timed out"), GPTOSSTimeoutError),
            (httpx.ReadTimeout("timed out"), GPTOSSTimeoutError),
            (APITimeoutError(request=Mock()), GPTOSSTimeoutError),
        ],
    )
    def test_timeout_errors_are_normalized(self, exception, expected):
        client = self._client(valid_response())
        client.chat.completions.create.side_effect = exception

        with pytest.raises(expected):
            GPTOSSService(client=client, model="test-model").analyze(**INPUT_PAYLOAD)

    def test_rate_limit_errors_are_normalized(self):
        client = self._client(valid_response())
        error = RuntimeError("rate limited")
        error.status_code = 429
        client.chat.completions.create.side_effect = error

        with pytest.raises(GPTOSSRateLimitError):
            GPTOSSService(client=client, model="test-model").analyze(**INPUT_PAYLOAD)

    def test_missing_novel_metadata_is_rejected_before_analysis(self):
        with pytest.raises(InsufficientNovelDataError):
            build_ai_payload(
                {"metadata": None, "reviews": []},
                INPUT_PAYLOAD["user_preference"],
            )

    def test_invalid_evidence_is_rejected_without_api_call(self):
        client = self._client(
            valid_response(
                sources=[
                    {
                        "evidence_id": REVIEW["review_id"],
                        "source": "forged.example.test",
                        "url": REVIEW["url"],
                    }
                ]
            )
        )
        service = GPTOSSService(client=client, model="test-model")

        with pytest.raises(GPTOSSInvalidResponseError):
            service.analyze(**INPUT_PAYLOAD)

    def test_nvidia_api_key_is_read_from_environment(self):
        client_factory = Mock()
        with patch.dict(
            "os.environ",
            {
                "NVIDIA_API_KEY": "nvidia-test-key",
                "GPT_OSS_BASE_URL": "https://nvidia.example.test/v1",
                "GPT_OSS_MODEL": "test-model",
            },
            clear=True,
        ), patch("backend.services.gpt_oss_service.OpenAI", client_factory):
            GPTOSSService()

        assert client_factory.call_args.kwargs["api_key"] == "nvidia-test-key"
        assert client_factory.call_args.kwargs["base_url"] == "https://nvidia.example.test/v1"

    def test_missing_configuration_is_reported(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(GPTOSSConfigurationError):
                GPTOSSService()

    def test_invalid_timeout_configuration_is_reported(self):
        with patch.dict(
            "os.environ",
            {
                "NVIDIA_API_KEY": "test-key",
                "GPT_OSS_BASE_URL": "https://nvidia.example.test/v1",
                "GPT_OSS_MODEL": "test-model",
                "GPT_OSS_READ_TIMEOUT_SECONDS": "0",
            },
            clear=True,
        ):
            with pytest.raises(GPTOSSConfigurationError):
                GPTOSSService()
