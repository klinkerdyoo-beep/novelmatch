import json
import unittest
from dataclasses import dataclass
from typing import Any

from backend.services.gemini_service import GeminiAIService


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


@dataclass(frozen=True)
class QualityCase:
    name: str
    user_preference: dict[str, Any]
    novel: dict[str, Any]
    reviews: list[dict[str, Any]]
    response: dict[str, Any]
    expected_score: int | None
    expected_level: str | None
    required_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    required_limitation: str | None = None


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


REVIEWS = [
    {
        "review_id": "r1",
        "text": "The world-building is vivid and the protagonist is brave.",
        "source": "Reader A",
        "url": "https://example.test/r1",
    },
    {
        "review_id": "r2",
        "text": "The pacing is slow, but the characters are compelling.",
        "source": "Reader B",
        "url": "https://example.test/r2",
    },
]


def review_source(review_id: str) -> dict[str, str]:
    review = next(review for review in REVIEWS if review["review_id"] == review_id)
    return {
        "evidence_id": review["review_id"],
        "source": review["source"],
        "url": review["url"],
    }


QUALITY_CASES = [
    QualityCase(
        name="strong match",
        user_preference={"liked_genres": ["Fantasy", "Adventure"]},
        novel={"genres": ["Fantasy", "Adventure"], "description": "A brave hero explores a magical world."},
        reviews=REVIEWS[:1],
        response=response_template(
            score=88,
            level="High",
            matches=[{"point": "Fantasy adventure", "explanation": "The genres align.", "evidence_ids": []}],
            positive=["Readers praised the world-building."],
            sources=[review_source("r1")],
        ),
        expected_score=88,
        expected_level="High",
        required_terms=("fantasy", "adventure"),
    ),
    QualityCase(
        name="weak match",
        user_preference={"liked_genres": ["Romance"], "disliked_genres": ["Horror"]},
        novel={"genres": ["Horror"], "description": "A supernatural investigation."},
        reviews=[],
        response=response_template(
            score=25,
            level="Low",
            mismatches=[{"point": "Horror genre", "explanation": "It conflicts with the disliked genre.", "evidence_ids": []}],
        ),
        expected_score=25,
        expected_level="Low",
        required_terms=("horror", "disliked"),
    ),
    QualityCase(
        name="mixed match",
        user_preference={"liked_genres": ["Fantasy"], "story_preferences": ["Fast-paced"]},
        novel={"genres": ["Fantasy"], "description": "A fantasy quest with a slow opening."},
        reviews=REVIEWS,
        response=response_template(
            score=68,
            level="Medium",
            matches=[{"point": "Fantasy", "explanation": "The genre matches.", "evidence_ids": []}],
            mismatches=[{"point": "Pacing", "explanation": "A review describes slow pacing.", "evidence_ids": ["r2"]}],
            positive=["Compelling characters."],
            negative=["Slow pacing."],
            sources=[review_source("r2")],
        ),
        expected_score=68,
        expected_level="Medium",
        required_terms=("fantasy", "pacing"),
    ),
    QualityCase(
        name="conflicting reviews",
        user_preference={"story_preferences": ["Strong characters"]},
        novel={"description": "A character-focused journey."},
        reviews=REVIEWS,
        response=response_template(
            score=70,
            level="Medium",
            matches=[{"point": "Characters", "explanation": "Reviews describe compelling characters.", "evidence_ids": ["r2"]}],
            positive=["The protagonist is brave."],
            negative=["The pacing is slow."],
            mixed=["Reviews differ on the reading experience."],
            sources=[review_source("r1"), review_source("r2")],
        ),
        expected_score=70,
        expected_level="Medium",
        required_terms=("characters", "reviews", "differ"),
    ),
    QualityCase(
        name="insufficient evidence",
        user_preference={"liked_genres": ["Mystery"]},
        novel={},
        reviews=[],
        response=response_template(
            score=None,
            level=None,
            limitations=["Novel information is insufficient to calculate a score."],
        ),
        expected_score=None,
        expected_level=None,
        required_limitation="insufficient",
    ),
    QualityCase(
        name="no reviews",
        user_preference={"liked_genres": ["Fantasy"]},
        novel={"genres": ["Fantasy"], "description": "A fantasy journey."},
        reviews=[],
        response=response_template(
            score=75,
            level="Medium",
            matches=[{"point": "Fantasy", "explanation": "The novel genre matches.", "evidence_ids": []}],
            limitations=["No relevant reader reviews were provided."],
        ),
        expected_score=75,
        expected_level="Medium",
        required_limitation="no relevant reader reviews",
    ),
    QualityCase(
        name="character preferences",
        user_preference={"character_preferences": ["Independent protagonist"]},
        novel={"description": "An independent protagonist solves the central mystery."},
        reviews=[],
        response=response_template(
            score=82,
            level="High",
            matches=[{"point": "Independent protagonist", "explanation": "The description states this trait.", "evidence_ids": []}],
        ),
        expected_score=82,
        expected_level="High",
        required_terms=("independent", "protagonist"),
    ),
    QualityCase(
        name="rated novel similarity",
        user_preference={"rated_novels": [{"title": "The Hobbit", "rating": 5}]},
        novel={"title": "A fantasy quest", "description": "A small hero travels through a magical land."},
        reviews=[],
        response=response_template(
            score=80,
            level="High",
            matches=[{"point": "Rated novel similarity", "explanation": "The quest structure is similar to The Hobbit based on the provided descriptions.", "evidence_ids": []}],
        ),
        expected_score=80,
        expected_level="High",
        required_terms=("similar", "the hobbit"),
    ),
    QualityCase(
        name="unsupported-claim trap",
        user_preference={"liked_genres": ["Fantasy"]},
        novel={"genres": ["Fantasy"], "description": "A journey through an unnamed land."},
        reviews=[],
        response=response_template(
            score=60,
            level="Medium",
            matches=[{"point": "Fantasy genre", "explanation": "The supplied genre is Fantasy.", "evidence_ids": []}],
            limitations=["Character, romance, and pacing information were not provided."],
        ),
        expected_score=60,
        expected_level="Medium",
        forbidden_terms=("dragon", "romance subplot", "fast-paced"),
        required_limitation="not provided",
    ),
    QualityCase(
        name="evidence/source correctness",
        user_preference={"liked_genres": ["Fantasy"]},
        novel={"genres": ["Fantasy"]},
        reviews=REVIEWS,
        response=response_template(
            score=65,
            level="Medium",
            matches=[{"point": "World-building", "explanation": "Reader A explicitly praises it.", "evidence_ids": ["r1"]}],
            mismatches=[{"point": "Pacing", "explanation": "Reader B calls the pacing slow.", "evidence_ids": ["r2"]}],
            sources=[review_source("r1"), review_source("r2")],
        ),
        expected_score=65,
        expected_level="Medium",
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
        ).analyze(
            user_preference=case.user_preference,
            novel=case.novel,
            reviews=case.reviews,
        )
        serialized = result.model_dump_json().lower()
        review_by_id = {review["review_id"]: review for review in case.reviews}

        evidence_ids = {
            evidence_id
            for point in [*result.matches, *result.mismatches]
            for evidence_id in point.evidence_ids
        }
        if not evidence_ids.issubset(review_by_id):
            checks["evidence_consistency"] = "FAIL"
            errors.append("analysis contains an unknown evidence ID")
        for source in result.sources:
            review = review_by_id.get(source.evidence_id)
            if not review or any(
                review.get(field) != getattr(source, field)
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

        if (
            result.match_score != case.expected_score
            or result.match_level != case.expected_level
        ):
            checks["scoring_reasoning"] = "FAIL"
            errors.append("score or level does not match the expected reasoning band")
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
