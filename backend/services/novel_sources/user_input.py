"""Accept the frontend form JSON and prepare book metadata for AI handoff.

This module deliberately stops before calling an AI provider or exposing an API
route. It adapts the user-facing form schema to the existing research and AI
payload contracts.
"""

from __future__ import annotations

from typing import Any

from .ai_payload import build_ai_payload
from .service import NovelResearchService


def normalize_user_input(value: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate the agreed form JSON and map preferences to the internal schema."""
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    if set(value) != {"target_novel", "user_preferences"}:
        raise ValueError("input must contain only target_novel and user_preferences")

    target = value["target_novel"]
    if not isinstance(target, dict) or set(target) - {"title", "author", "synopsis", "source_url"}:
        raise ValueError("target_novel must contain title, author, and optional synopsis/source_url")
    title = _required_text(target.get("title"), "target_novel.title", 300)
    author = _required_text(target.get("author"), "target_novel.author", 300)
    synopsis = target.get("synopsis")
    if synopsis is not None and (not isinstance(synopsis, str) or len(synopsis) > 20000):
        raise ValueError("target_novel.synopsis must be text of at most 20000 characters")
    source_url = target.get("source_url")
    if source_url is not None and not isinstance(source_url, str):
        raise ValueError("target_novel.source_url must be a URL string")

    preferences = value["user_preferences"]
    if not isinstance(preferences, dict) or set(preferences) - {
        "genre_preferences", "character_preferences", "story_element_preferences"
    }:
        raise ValueError("user_preferences contains an unknown field or is not an object")

    genres = _section(preferences, "genre_preferences", {"liked_genres", "disliked_genres"})
    characters = _section(preferences, "character_preferences", {
        "liked_traits", "liked_character_description", "disliked_character_description"
    })
    stories = _section(preferences, "story_element_preferences", {"liked_elements", "disliked_elements"})

    character_preferences = [f"Likes: {item}" for item in _string_list(characters, "liked_traits")]
    for field in ("liked_character_description", "disliked_character_description"):
        text = characters.get(field, "")
        if not isinstance(text, str):
            raise ValueError(f"user_preferences.character_preferences.{field} must be text")
        if text.strip():
            label = "Likes" if field.startswith("liked_") else "Dislikes"
            character_preferences.append(f"{label}: {text.strip()}")

    story_preferences = [f"Likes: {item}" for item in _string_list(stories, "liked_elements")]
    story_preferences.extend(f"Dislikes: {item}" for item in _string_list(stories, "disliked_elements"))

    return (
        {
            "title": title,
            "author": author,
            "synopsis": synopsis.strip() if synopsis else "",
            "source_url": source_url.strip() if source_url else "",
        },
        {
            "liked_genres": _string_list(genres, "liked_genres"),
            "disliked_genres": _string_list(genres, "disliked_genres"),
            "character_preferences": character_preferences,
            "story_preferences": story_preferences,
            "rated_novels": [],
        },
    )


async def prepare_novel_analysis_input(
    value: dict[str, Any],
    *,
    research_service: NovelResearchService | None = None,
    limit: int = 5,
    page: int = 1,
) -> dict[str, Any]:
    """Search book metadata and return research plus a ready-to-forward AI payload.

    No AI request is made. If no matching metadata is found, ``ai_payload`` is
    ``None`` and callers can use the research warnings to ask for better input.
    """
    target, user_preference = normalize_user_input(value)
    service = research_service or NovelResearchService()
    research = await service.search(
        target["title"],
        target["author"],
        user_provided_description=target["synopsis"] or None,
        limit=limit,
        page=page,
    )
    research_data = research.to_dict()
    # The synopsis may be retained as user input by the search service when no
    # provider match exists. It is useful to show in research, but must not be
    # treated as provider metadata for the downstream analysis handoff.
    has_provider_metadata = research.metadata and research.metadata.provider != "user_input"
    ai_payload = build_ai_payload(research, user_preference) if has_provider_metadata else None
    return {"research": research_data, "ai_payload": ai_payload}


def _section(parent: dict[str, Any], name: str, allowed: set[str]) -> dict[str, Any]:
    section = parent.get(name, {})
    if not isinstance(section, dict) or set(section) - allowed:
        raise ValueError(f"user_preferences.{name} has an unknown field or is not an object")
    return section


def _string_list(section: dict[str, Any], field: str) -> list[str]:
    values = section.get(field, [])
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise ValueError(f"{field} must be a list of strings")
    return [item.strip() for item in values if item.strip()]


def _required_text(value: Any, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{field} must contain 1 to {max_length} characters")
    return value.strip()
