import json
import unittest

from backend.services.gemini_service import (
    GeminiAIService,
    GeminiInvalidResponseError,
)


REVIEWS = [
    {
        "review_id": "review-1",
        "text": "Excellent world-building.",
        "source": "Test",
        "url": "https://example.com/review/1",
    }
]


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeModels:
    def __init__(self, response: FakeResponse):
        self.response = response

    def generate_content(self, **kwargs):
        return self.response


class FakeClient:
    def __init__(self, response_text: str):
        self.models = FakeModels(FakeResponse(response_text))


def valid_response(**overrides):
    response = {
        "match_score": 86,
        "match_level": "High",
        "matches": [
            {
                "point": "World-building",
                "explanation": "The review praises it.",
                "evidence_ids": ["review-1"],
            }
        ],
        "mismatches": [],
        "review_summary": {
            "positive": ["Excellent world-building."],
            "negative": [],
            "mixed": [],
        },
        "sources": [
            {
                "evidence_id": "review-1",
                "source": "Test",
                "url": "https://example.com/review/1",
            }
        ],
        "limitations": [],
    }
    response.update(overrides)
    return json.dumps(response)


class GeminiResponseValidationTests(unittest.TestCase):
    def analyze(self, response_text):
        service = GeminiAIService(client=FakeClient(response_text))
        return service.analyze(
            user_preference={}, novel={}, reviews=REVIEWS
        )

    def assert_invalid(self, response_text):
        with self.assertRaises(GeminiInvalidResponseError):
            self.analyze(response_text)

    def test_valid_response(self):
        result = self.analyze(valid_response())
        self.assertEqual(result.match_level, "High")

    def test_invalid_score(self):
        self.assert_invalid(valid_response(match_score=101))

    def test_invalid_level(self):
        self.assert_invalid(valid_response(match_level="Great"))

    def test_score_level_mismatch(self):
        self.assert_invalid(valid_response(match_score=59, match_level="Medium"))

    def test_null_score_with_non_null_level(self):
        self.assert_invalid(valid_response(match_score=None, match_level="Low"))

    def test_invalid_evidence_id(self):
        self.assert_invalid(
            valid_response(
                matches=[
                    {
                        "point": "x",
                        "explanation": "y",
                        "evidence_ids": ["missing"],
                    }
                ]
            )
        )

    def test_invalid_source_reference(self):
        self.assert_invalid(
            valid_response(
                sources=[
                    {
                        "evidence_id": "review-1",
                        "source": "Other",
                        "url": "https://example.com/review/1",
                    }
                ]
            )
        )

    def test_malformed_json(self):
        self.assert_invalid("not JSON")

    def test_missing_field(self):
        payload = json.loads(valid_response())
        del payload["review_summary"]
        self.assert_invalid(json.dumps(payload))

    def test_empty_response(self):
        self.assert_invalid("   ")


if __name__ == "__main__":
    unittest.main()
