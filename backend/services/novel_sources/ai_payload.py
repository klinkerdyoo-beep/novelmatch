from __future__ import annotations

import copy
from typing import Any

from .models import NovelResearchResult


class InsufficientNovelDataError(ValueError):
    """The API should return seach warnings or ask the user to refine the query."""


def _normalize_user_preference(value: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "liked_genres",
        "disliked_genres",
        "character_preferences",
        "story_preferences",
        "rated_novels",
    )
    unknown = set(value) - set(fields)
    if unknown:
        raise ValueError(f"Unknown user_preference fields: {', '.join(sorted(unknown))}")

    normalized: dict[str, Any] = {}
    for field in fields[:-1]:
        items = value.get(field, [])
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise ValueError(f"user_preference.{field} must be a list of strings")
        normalized[field] = list(items)

    rated_novels = value.get("rated_novels", [])
    if not isinstance(rated_novels, list):
        raise ValueError("user_preference.rated_novels must be a list")
    normalized["rated_novels"] = []
    for item in rated_novels:
        if not isinstance(item, dict) or set(item) != {"title", "author", "rating"}:
            raise ValueError("Each rated_novel must contain only title, author, and rating")
        if not isinstance(item["title"], str) or not isinstance(item["author"], str):
            raise ValueError("rated_novel title and author must be strings")
        rating = item["rating"]
        if isinstance(rating, bool) or not isinstance(rating, (int, float)) or not 0 <= rating <= 5:
            raise ValueError("rated_novel rating must be a number from 0 to 5")
        normalized["rated_novels"].append(dict(item))
    return normalized


def build_ai_payload(result: NovelResearchResult | dict[str, Any],
                     user_preference: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(user_preference, dict):
        raise ValueError("user_preference must be an object")
    normalized_preference = _normalize_user_preference(user_preference)
    data = result.to_dict() if isinstance(result, NovelResearchResult) else copy.deepcopy(result)
    metadata = data.get("metadata")
    if not metadata:
        raise InsufficientNovelDataError("No selected novel. Return the search warnings before requesting AI analysis.")
    # Keep this payload limited to the agreed Gemini input schema. Search
    # warnings and general metadata references remain on the research result;
    # they are not novel fields in the AI contract.
    reviews = []
    ids = set()
    for item in data.get("reviews", []):
        review_id = item.get("review_id")
        if not review_id or review_id in ids:
            raise ValueError("Every review must have a unique review_id")
        ids.add(review_id)
        reviews.append({
            "review_id": review_id,
            "text": item["snippet"],
            # Review sources generally provide snippets, not a verified rating.
            "rating": None,
            "source": item["source_name"],
            "url": item["url"],
        })
    novel = {
        "title": metadata["title"],
        "author": list(metadata.get("authors") or []),
        "genres": list(metadata.get("genres") or []),
        "description": metadata.get("description"),
        "publisher": metadata.get("publisher"),
        "published_date": (
            str(metadata["published_year"])
            if metadata.get("published_year") is not None
            else None
        ),
        "rating": metadata.get("average_rating"),
        "rating_count": metadata.get("ratings_count"),
    }
    return {"user_preference": normalized_preference, "novel": novel, "reviews": reviews}


def validate_analysis_evidence(analysis: dict[str, Any], payload: dict[str, Any]) -> None:
    """Optional post-analysis guard for Person 2; does not assess semantic faithfulness."""
    allowed = {r["review_id"]: r for r in payload["reviews"]}
    cited = set()
    for source in analysis.get("sources", []):
        evidence_id = source.get("evidence_id")
        original = allowed.get(evidence_id)
        if original is None or source.get("url") != original["url"] or source.get("source") != original["source"]:
            raise ValueError("AI returned an unknown or altered source")
        cited.add(evidence_id)
    for point in analysis.get("matches", []) + analysis.get("mismatches", []):
        for evidence_id in point.get("evidence_ids", []):
            if evidence_id not in allowed or evidence_id not in cited:
                raise ValueError("AI returned an unknown or uncited evidence_id")


def merge_analysis_limitations(
    analysis: dict[str, Any],
    payload: dict[str, Any],
    research_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Add sourcing warnings to the result without putting them in AI input."""
    output = copy.deepcopy(analysis)
    # The fallback supports older payloads while callers migrate to passing
    # warnings separately from the strict AI input object.
    warnings = research_warnings
    if warnings is None:
        warnings = payload.get("novel", {}).get("data_limitations", [])
    output["limitations"] = list(dict.fromkeys(warnings + output.get("limitations", [])))
    return output
