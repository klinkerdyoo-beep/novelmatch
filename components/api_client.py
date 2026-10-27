"""Small client for the NovelMatch backend analysis endpoint."""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class NovelMatchAPIError(RuntimeError):
    """Raised when the backend cannot return an analysis."""


def _request(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    base_url = os.getenv("NOVELMATCH_API_URL", "https://novel-api.fastapicloud.dev")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        response = requests.request(
            method,
            f"{base_url}{path}",
            headers=headers,
            json=json,
            timeout=timeout or float(os.getenv("NOVELMATCH_API_TIMEOUT_SECONDS", "90")),
        )
    except requests.RequestException as exc:
        raise NovelMatchAPIError(
            "The backend service is unavailable. Start the backend and try again."
        ) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise NovelMatchAPIError("The backend returned invalid JSON.") from exc
    if not response.ok:
        detail = payload.get("detail", response.text) if isinstance(payload, dict) else response.text
        raise NovelMatchAPIError(str(detail) or "The backend request failed.")
    if not isinstance(payload, dict):
        raise NovelMatchAPIError("The backend returned an invalid response.")
    return payload


def login(username_or_email: str, password: str) -> dict[str, Any]:
    return _request("POST", "/auth/login", json={"email": username_or_email, "password": password})

def get_user_info(token: str) -> dict[str, Any]:
    return _request("GET", "/auth/me", token=token)

def signup(name: str, email: str, password: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/auth/signup",
        json={"name": name, "email": email, "password": password},
    )


def save_preferences(preferences: dict[str, Any], token: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/preferences",
        json=preferences,
        token=token,
    )


def get_preferences(token: str) -> dict[str, Any]:
    return _request("GET", "/preferences", token=token)


def analyze_novel(payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    return _request("POST", "/analysis", json=payload, token=token, timeout=90.0)

def get_novel_info(novel_id: str, token: str) -> dict[str, Any]:
    return _request("GET", f"/novels/{novel_id}", token=token)


def get_analysis_novel(novel_id: str, token: str) -> dict[str, Any]:
    return _request("GET", f"/analysis/{novel_id}", token=token)


get_analyze_novel = get_analysis_novel


def get_user_history(token: str) -> dict[str, Any]:
    return _request("GET", "/history", token=token)


def logout_user(token: str) -> None:
    """Call backend to revoke the Supabase session (invalidates the token everywhere)."""
    try:
        _request("POST", "/auth/logout", token=token)
    except NovelMatchAPIError:
        pass
