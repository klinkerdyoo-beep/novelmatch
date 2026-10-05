from __future__ import annotations

import copy
from typing import Any

from .models import NovelResearchResult


class InsufficientNovelDataError(ValueError):
    """The API should return seach warnings or ask the user to refine the query."""


def build_ai_payload(result: NovelResearchResult | dict[str, Any],
                     user_preference: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(user_preference, dict):
        raise ValueError("user_preference must be an object")
    data = result.to_dict() if isinstance(result, NovelResearchResult) else copy.deepcopy(result)
    metadata = data.get("metadata")
    if not metadata:
        raise InsufficientNovelDataError("No selected novel. Return the search warnings before requesting AI analysis.")
    reviews = []
    ids = set()
    for item in data.get("reviews", []):
        review_id = item.get("review_id")
        if not review_id or review_id in ids:
            raise ValueError("Every review must have a unique review_id")
        ids.add(review_id)
        reviews.append({"review_id": review_id, "text": item["snippet"],
                        "rating": None, "source": item["source_name"], "url": item["url"]})
    novel = {"title": metadata["title"], "author": list(metadata["authors"]),
             "genres": metadata["genres"], "description": metadata["description"],
             "description_source": metadata["description_source"],
             "publisher": None,
             "published_date": str(metadata["published_year"]) if metadata["published_year"] is not None else None,
             "rating": metadata["average_rating"], "rating_count": metadata["ratings_count"],
             "sources": data.get("sources", []),
             "data_limitations": data.get("warnings", []),
             "metadata_status": "user_provided" if metadata["provider"] == "user_input" else "provider_matched"}
    return {"user_preference": copy.deepcopy(user_preference), "novel": novel, "reviews": reviews}


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


def merge_analysis_limitations(analysis: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Preserve source warnings in the API response even if the model omits them."""
    output = copy.deepcopy(analysis)
    output["limitations"] = list(dict.fromkeys(payload["novel"]["data_limitations"] + output.get("limitations", [])))
    return output
