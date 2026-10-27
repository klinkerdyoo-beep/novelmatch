import json
import unittest
from dataclasses import dataclass
from typing import Any

from backend.services.gemini_service import GeminiAIService
from backend.services.novel_sources.ai_payload import build_ai_payload


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeModels:
    def __init__(self, text: str):
        self.text = text

    def generate_content(self, **kwargs):
        return FakeResponse(self.text)


class FakeClient:
    def __init__(self, text: str):
        self.models = FakeModels(text)


def make_payload(
    user_preference: dict[str, Any],
    *,
    title: str = "Test Novel",
    authors: list[str] | None = None,
    description: str | None = "A supplied novel description.",
    genres: list[str] | None = None,
    published_year: int | None = 2020,
    average_rating: float | None = 4.2,
    ratings_count: int | None = 100,
    reviews: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build the exact AI input shape through the production payload adapter."""

    research_result = {
        "metadata": {
            "title": title,
            "authors": authors or ["Test Author"],
            "description": description,
            "description_source": "google_books" if description else None,
            "published_year": published_year,
            "genres": genres or [],
            "average_rating": average_rating,
            "ratings_count": ratings_count,
            "cover_url": None,
            "provider": "google_books",
            "source_url": "https://books.example.test/test-novel",
            "provider_id": "test-novel",
            "match_score": 1.0,
            "sources": [],
        },
        "reviews": reviews or [],
        "sources": [],
        "warnings": warnings or [],
    }
    return build_ai_payload(research_result, user_preference)


def review(
    review_id: str,
    snippet: str,
    source_name: str = "reader.example.test",
    url: str | None = None,
) -> dict[str, Any]:
    return {
        "title": "Test Novel review",
        "url": url or f"https://{source_name}/{review_id}",
        "snippet": snippet,
        "source_name": source_name,
        "relevance_score": 0.95,
        "published_date": "2025-01-01",
        "review_id": review_id,
        "evidence_type": "review_excerpt_candidate",
        "verification_status": "heuristic_only",
    }


def response_template(
    *,
    score: int | None,
    level: str | None,
    matches: list[dict[str, Any]] | None = None,
    mismatches: list[dict[str, Any]] | None = None,
    positive: list[str] | None = None,
    negative: list[str] | None = None,
    mixed: list[str] | None = None,
    sources: list[dict[str, str]] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "match_score": score,
        "match_level": level,
        "matches": matches or [],
        "mismatches": mismatches or [],
        "review_summary": {
            "positive": positive or [],
            "negative": negative or [],
            "mixed": mixed or [],
        },
        "sources": sources or [],
        "limitations": limitations or [],
    }


@dataclass(frozen=True)
class QualityCase:
    name: str
    payload: dict[str, Any]
    response: dict[str, Any]
    expected_level: str | None
    expected_score_range: tuple[int, int] | None
    required_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    required_limitation: str | None = None


REVIEWS = [
    review(
        "r1",
        "The world-building is vivid and the pacing is fast.",
        source_name="reader-a.example.test",
    ),
    review(
        "r2",
        "The world-building is vivid, but the pacing is slow.",
        source_name="reader-b.example.test",
    ),
]


def payload_review_source(payload: dict[str, Any], review_id: str) -> dict[str, str]:
    item = next(item for item in payload["reviews"] if item["review_id"] == review_id)
    return {
        "evidence_id": item["review_id"],
        "source": item["source"],
        "url": item["url"],
    }


STRONG_PAYLOAD = make_payload(
    {"liked_genres": ["Fantasy", "Adventure"]},
    title="The Bright Quest",
    genres=["Fantasy", "Adventure"],
    description="A brave hero explores a magical world.",
    reviews=REVIEWS[:1],
)
WEAK_PAYLOAD = make_payload(
    {"liked_genres": ["Romance"], "disliked_genres": ["Horror"]},
    genres=["Horror"],
    description="A supernatural investigation.",
)
MIXED_PAYLOAD = make_payload(
    {"liked_genres": ["Fantasy"], "story_preferences": ["Fast-paced"]},
    genres=["Fantasy"],
    description="A fantasy quest with an opening whose pacing is not specified.",
    reviews=REVIEWS,
)
CONFLICTING_PAYLOAD = make_payload(
    {"story_preferences": ["Fast-paced"]},
    description="A character-focused journey.",
    reviews=REVIEWS,
)


QUALITY_CASES = [
    QualityCase(
        name="strong match",
        payload=STRONG_PAYLOAD,
        response=response_template(
            score=88,
            level="High",
            matches=[{"point": "Fantasy adventure", "explanation": "The genres align.", "evidence_ids": []}],
            positive=["Reader A praises the world-building."],
            sources=[payload_review_source(STRONG_PAYLOAD, "r1")],
        ),
        expected_level="High",
        expected_score_range=(80, 100),
        required_terms=("fantasy", "adventure"),
    ),
    QualityCase(
        name="weak match",
        payload=WEAK_PAYLOAD,
        response=response_template(
            score=25,
            level="Low",
            mismatches=[{"point": "Horror genre", "explanation": "It conflicts with the disliked genre.", "evidence_ids": []}],
        ),
        expected_level="Low",
        expected_score_range=(0, 59),
        required_terms=("horror", "disliked"),
    ),
    QualityCase(
        name="mixed match",
        payload=MIXED_PAYLOAD,
        response=response_template(
            score=68,
            level="Medium",
            matches=[{"point": "Fantasy", "explanation": "The genre matches.", "evidence_ids": []}],
            mismatches=[{"point": "Pacing", "explanation": "Reader B describes slow pacing.", "evidence_ids": ["r2"]}],
            positive=["Reader opinions include vivid world-building."],
            negative=["Reader B reports slow pacing."],
            sources=[payload_review_source(MIXED_PAYLOAD, "r2")],
        ),
        expected_level="Medium",
        expected_score_range=(60, 79),
        required_terms=("fantasy", "pacing"),
    ),
    QualityCase(
        name="conflicting reviews",
        payload=CONFLICTING_PAYLOAD,
        response=response_template(
            score=70,
            level="Medium",
            matches=[{"point": "Fast pacing", "explanation": "Reader A describes fast pacing.", "evidence_ids": ["r1"]}],
            mismatches=[{"point": "Slow pacing", "explanation": "Reader B describes slow pacing.", "evidence_ids": ["r2"]}],
            mixed=["Readers give opposing opinions about pacing."],
            sources=[
                payload_review_source(CONFLICTING_PAYLOAD, "r1"),
                payload_review_source(CONFLICTING_PAYLOAD, "r2"),
            ],
        ),
        expected_level="Medium",
        expected_score_range=(60, 79),
        required_terms=("fast pacing", "slow pacing", "opposing"),
    ),
    QualityCase(
        name="insufficient evidence",
        payload=make_payload(
            {"liked_genres": ["Mystery"]},
            description=None,
            genres=[],
            published_year=None,
            average_rating=None,
            ratings_count=None,
            warnings=["Missing novel metadata: description, genres, published_year."],
        ),
        response=response_template(
            score=None,
            level=None,
            limitations=["Novel information is insufficient to calculate a score."],
        ),
        expected_level=None,
        expected_score_range=None,
        required_limitation="insufficient",
    ),
    QualityCase(
        name="no reviews",
        payload=make_payload(
            {"liked_genres": ["Fantasy"]},
            genres=["Fantasy"],
            description="A fantasy journey.",
            warnings=["No sufficiently relevant review excerpts passed screening."],
        ),
        response=response_template(
            score=75,
            level="Medium",
            matches=[{"point": "Fantasy", "explanation": "The novel genre matches.", "evidence_ids": []}],
            limitations=["No relevant reader reviews were provided."],
        ),
        expected_level="Medium",
        expected_score_range=(60, 79),
        required_limitation="no relevant reader reviews",
    ),
    QualityCase(
        name="character preferences",
        payload=make_payload(
            {"character_preferences": ["Independent protagonist"]},
            description="An independent protagonist solves the central mystery.",
        ),
        response=response_template(
            score=82,
            level="High",
            matches=[{"point": "Independent protagonist", "explanation": "The description states this trait.", "evidence_ids": []}],
        ),
        expected_level="High",
        expected_score_range=(80, 100),
        required_terms=("independent", "protagonist"),
    ),
    QualityCase(
        name="rated novel similarity",
        payload=make_payload(
            {
                "rated_novels": [
                    {
                        "title": "The Hobbit",
                        "author": "J.R.R. Tolkien",
                        "rating": 5,
                    }
                ]
            },
            title="A Small Magical Quest",
            genres=["Fantasy", "Adventure"],
            description="A small hero travels through a dangerous magical land.",
        ),
        response=response_template(
            score=80,
            level="High",
            matches=[{"point": "Rated novel similarity", "explanation": "The supplied genre and description metadata are similar to The Hobbit.", "evidence_ids": []}],
        ),
        expected_level="High",
        expected_score_range=(80, 100),
        required_terms=("similar", "the hobbit", "description"),
    ),
    QualityCase(
        name="unsupported-claim trap",
        payload=make_payload(
            {"liked_genres": ["Fantasy"]},
            genres=["Fantasy"],
            description="A journey through an unnamed land.",
        ),
        response=response_template(
            score=60,
            level="Medium",
            matches=[{"point": "Fantasy genre", "explanation": "The supplied genre is Fantasy.", "evidence_ids": []}],
            limitations=["Character, romance, and pacing information were not provided."],
        ),
        expected_level="Medium",
        expected_score_range=(60, 79),
        forbidden_terms=("dragon", "romance subplot", "fast-paced"),
        required_limitation="not provided",
    ),
    QualityCase(
        name="evidence/source correctness",
        payload=make_payload(
            {"liked_genres": ["Fantasy"]},
            genres=["Fantasy"],
            reviews=REVIEWS,
        ),
        response=response_template(
            score=65,
            level="Medium",
            matches=[{"point": "World-building", "explanation": "Reader A explicitly praises it.", "evidence_ids": ["r1"]}],
            mismatches=[{"point": "Pacing", "explanation": "Reader B calls the pacing slow.", "evidence_ids": ["r2"]}],
            sources=[
                {"evidence_id": "r1", "source": "reader-a.example.test", "url": "https://reader-a.example.test/r1"},
                {"evidence_id": "r2", "source": "reader-b.example.test", "url": "https://reader-b.example.test/r2"},
            ],
        ),
        expected_level="Medium",
        expected_score_range=(60, 79),
        required_terms=("world-building", "pacing"),
    ),
]


def evaluate_case(case: QualityCase) -> dict[str, Any]:
    checks = {
        "evidence_consistency": "PASS",
        "preference_relevance": "PASS",
        "unsupported_claims": "PASS",
        "scoring_reasoning": "PASS",
    }
    errors: list[str] = []
    try:
        result = GeminiAIService(
            client=FakeClient(json.dumps(case.response))
        ).analyze(**case.payload)
        serialized = result.model_dump_json().lower()
        review_by_id = {review["review_id"]: review for review in case.payload["reviews"]}

        evidence_ids = {
            evidence_id
            for point in [*result.matches, *result.mismatches]
            for evidence_id in point.evidence_ids
        }
        if not evidence_ids.issubset(review_by_id):
            checks["evidence_consistency"] = "FAIL"
            errors.append("analysis contains an unknown evidence ID")
        for source in result.sources:
            review_item = review_by_id.get(source.evidence_id)
            if not review_item or any(
                review_item.get(field) != getattr(source, field)
                for field in ("source", "url")
            ):
                checks["evidence_consistency"] = "FAIL"
                errors.append("analysis contains an incorrect source reference")

        if any(term.lower() not in serialized for term in case.required_terms):
            checks["preference_relevance"] = "FAIL"
            errors.append("required preference/reasoning term is absent")

        if any(term.lower() in serialized for term in case.forbidden_terms):
            checks["unsupported_claims"] = "FAIL"
            errors.append("unsupported claim detected")
        if case.required_limitation and case.required_limitation.lower() not in serialized:
            checks["unsupported_claims"] = "FAIL"
            errors.append("required limitation is absent")

        score = result.match_score
        if case.expected_score_range is None:
            score_is_valid = score is None
        else:
            score_is_valid = score is not None and case.expected_score_range[0] <= score <= case.expected_score_range[1]
        if not score_is_valid or result.match_level != case.expected_level:
            checks["scoring_reasoning"] = "FAIL"
            errors.append("score or level is outside the expected justified band")
    except Exception as exc:  # Evaluation output should record, not hide, failures.
        for criterion in checks:
            checks[criterion] = "FAIL"
        errors.append(f"analysis validation raised {type(exc).__name__}: {exc}")

    return {
        "case": case.name,
        "criteria": checks,
        "overall": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "errors": errors,
    }


class AnalysisQualityEvaluationTests(unittest.TestCase):
    def test_analysis_quality_evaluation(self):
        results = [evaluate_case(case) for case in QUALITY_CASES]
        print(json.dumps({
            "cases": results,
            "overall": "PASS" if all(item["overall"] == "PASS" for item in results) else "FAIL",
            "errors": [error for item in results for error in item["errors"]],
            "recommended_improvements": [
                "Add human-reviewed golden responses for scoring and relevance calibration.",
                "Add adversarial regression cases whenever unsupported claims are found.",
            ],
        }, indent=2))
        self.assertTrue(all(item["overall"] == "PASS" for item in results))


if __name__ == "__main__":
    unittest.main()
