import json
import unittest

from backend.services.gemini_service import (
    GeminiAIService,
    GeminiInvalidResponseError,
)
from backend.services.novel_sources.ai_payload import build_ai_payload


def build_test_payload() -> dict:
    """Build the same novel/review input shape used by the AI integration."""

    return build_ai_payload(
        {
            "metadata": {
                "title": "The Bright Quest",
                "authors": ["Test Author"],
                "description": "A brave hero explores a magical world.",
                "description_source": "google_books",
                "published_year": 2020,
                "genres": ["Fantasy", "Adventure"],
                "average_rating": 4.2,
                "ratings_count": 100,
                "cover_url": None,
                "provider": "google_books",
                "source_url": "https://books.example.test/the-bright-quest",
                "provider_id": "bright-quest-1",
                "match_score": 1.0,
                "sources": [],
            },
            "reviews": [
                {
                    "title": "The Bright Quest review",
                    "url": "https://reader.example.test/review-1",
                    "snippet": "The world-building is vivid and memorable.",
                    "source_name": "reader.example.test",
                    "relevance_score": 0.95,
                    "published_date": "2025-01-01",
                    "review_id": "review-1",
                    "evidence_type": "review_excerpt_candidate",
                    "verification_status": "heuristic_only",
                }
            ],
            "sources": [],
            "warnings": [],
        },
        {
            "liked_genres": ["Fantasy", "Adventure"],
            "disliked_genres": [],
            "character_preferences": ["Brave protagonist"],
            "story_preferences": ["World-building"],
            "rated_novels": [],
        },
    )


INPUT_PAYLOAD = build_test_payload()
REVIEW = INPUT_PAYLOAD["reviews"][0]


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
    """Return only fields defined by MatchAnalysis and its nested models."""

    response = {
        "match_score": 86,
        "match_level": "High",
        "matches": [
            {
                "point": "Fantasy adventure",
                "explanation": "The novel genres align with the preferences.",
                "evidence_ids": [REVIEW["review_id"]],
            }
        ],
        "mismatches": [],
        "review_summary": {
            "positive": ["The review praises the world-building."],
            "negative": [],
            "mixed": [],
        },
        "sources": [
            {
                "evidence_id": REVIEW["review_id"],
                "source": REVIEW["source"],
                "url": REVIEW["url"],
            }
        ],
        "limitations": [],
    }
    response.update(overrides)
    return json.dumps(response)


class GeminiResponseValidationTests(unittest.TestCase):
    """Slide-friendly coverage of the Gemini response validation boundary."""

    def analyze(self, response_text):
        service = GeminiAIService(client=FakeClient(response_text))
        return service.analyze(**INPUT_PAYLOAD)

    def assert_invalid(self, response_text):
        with self.assertRaises(GeminiInvalidResponseError):
            self.analyze(response_text)

    def test_valid_response(self):
        result = self.analyze(valid_response())
        self.assertEqual(result.match_level, "High")
        self.assertEqual(result.sources[0].evidence_id, REVIEW["review_id"])

    def test_invalid_score(self):
        self.assert_invalid(valid_response(match_score=101))

    def test_invalid_match_level(self):
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
                        "point": "Unsupported evidence",
                        "explanation": "This evidence is not in the input reviews.",
                        "evidence_ids": ["review-missing"],
                    }
                ]
            )
        )

    def test_invalid_source_reference(self):
        self.assert_invalid(
            valid_response(
                sources=[
                    {
                        "evidence_id": REVIEW["review_id"],
                        "source": "other.example.test",
                        "url": REVIEW["url"],
                    }
                ]
            )
        )

    def test_malformed_json(self):
        self.assert_invalid("not JSON")

    def test_missing_required_field(self):
        payload = json.loads(valid_response())
        del payload["review_summary"]
        self.assert_invalid(json.dumps(payload))

    def test_empty_response(self):
        self.assert_invalid("   ")


if __name__ == "__main__":
    unittest.main()
