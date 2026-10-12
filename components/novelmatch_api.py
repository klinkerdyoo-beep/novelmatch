"""Small client for the NovelMatch backend analysis endpoint."""

from __future__ import annotations

import os
from typing import Any

import requests


class NovelMatchAPIError(RuntimeError):
    """Raised when the backend cannot return an analysis."""


def analyze_novel(payload: dict[str, Any]) -> dict[str, Any]:
    base_url = os.getenv("NOVELMATCH_API_URL", "http://localhost:8000").rstrip("/")
    try:
        response = requests.post(
            f"{base_url}/analysis",
            json=payload,
            timeout=float(os.getenv("NOVELMATCH_API_TIMEOUT_SECONDS", "90")),
        )
    except requests.RequestException as exc:
        raise NovelMatchAPIError(
            "The analysis service is unavailable. Start the backend and try again."
        ) from exc
    except ValueError as exc:
        raise NovelMatchAPIError(
            "NOVELMATCH_API_TIMEOUT_SECONDS must be a valid number."
        ) from exc

    if response.ok:
        try:
            result = response.json()
        except ValueError as exc:
            raise NovelMatchAPIError("The analysis service returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise NovelMatchAPIError("The analysis service returned an invalid result.")
        return result

    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    raise NovelMatchAPIError(str(detail) or "The analysis request failed.")
