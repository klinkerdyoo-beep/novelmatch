from pathlib import Path
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from services.gemini_service import GeminiAIService, GeminiServiceError
from services.novel_sources import (
    InsufficientNovelDataError,
    NovelResearchService,
    build_ai_payload,
    merge_analysis_limitations,
)

app = FastAPI(title="NovelMatch API", version="1.0.0")


class NovelInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    author: str = Field(min_length=1, max_length=300)
    synopsis: str | None = Field(default=None, max_length=20000)


class GenrePreferences(BaseModel):
    liked_genres: list[str] = Field(default_factory=list)
    disliked_genres: list[str] = Field(default_factory=list)


class CharacterPreferences(BaseModel):
    liked_traits: list[str] = Field(default_factory=list)
    liked_character_description: str = ""
    disliked_character_description: str = ""


class StoryPreferences(BaseModel):
    liked_elements: list[str] = Field(default_factory=list)
    disliked_elements: list[str] = Field(default_factory=list)


class UserPreferences(BaseModel):
    genre_preferences: GenrePreferences = Field(default_factory=GenrePreferences)
    character_preferences: CharacterPreferences = Field(default_factory=CharacterPreferences)
    story_element_preferences: StoryPreferences = Field(default_factory=StoryPreferences)


class AnalysisRequest(BaseModel):
    target_novel: NovelInput
    user_preferences: UserPreferences


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

class SignupRequest(AuthCredentials):
    name: str = Field(min_length=1, max_length=200)


async def _supabase_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    headers = {"apikey": key, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(
                method,
                f"{url}/auth/v1{path}",
                headers=headers,
                json=json,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not reach Supabase.") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("msg") or response.json().get("message")
        except ValueError:
            detail = None
        raise HTTPException(
            status_code=response.status_code,
            detail=detail or "Supabase authentication request failed.",
        )
    return response.json()


async def require_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token is required.")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token is required.")

    try:
        user = await _supabase_request("GET", "/user", token=token)
    except HTTPException as exc:
        if exc.status_code in {401, 403}:
            raise HTTPException(status_code=401, detail="Invalid or expired session.") from exc
        raise
    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid Supabase user.")
    return user


# def _to_ai_preferences(preferences: UserPreferences) -> dict[str, Any]:
#     characters = preferences.character_preferences
#     stories = preferences.story_element_preferences
#     return {
#         "liked_genres": preferences.genre_preferences.liked_genres,
#         "disliked_genres": preferences.genre_preferences.disliked_genres,
#         "character_preferences": (
#             [f"Likes: {item}" for item in characters.liked_traits]
#             + ([f"Likes: {characters.liked_character_description}"]
#                if characters.liked_character_description.strip() else [])
#             + ([f"Dislikes: {characters.disliked_character_description}"]
#                if characters.disliked_character_description.strip() else [])
#         ),
#         "story_preferences": (
#             [f"Likes: {item}" for item in stories.liked_elements]
#             + [f"Dislikes: {item}" for item in stories.disliked_elements]
#         ),
#         "rated_novels": [],
#     }


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "NovelMatch backend is running"}


@app.post("/auth/signup")
async def signup(request: SignupRequest) -> dict[str, Any]:
    return await _supabase_request(
        "POST",
        "/signup",
        json={
            "email": request.email,
            "password": request.password,
            "data": {"name": request.name},
        },
    )



@app.post("/auth/login")
async def login(request: AuthCredentials) -> dict[str, Any]:
    return await _supabase_request(
        "POST",
        "/token?grant_type=password",
        json={"email": request.email, "password": request.password},
    )



@app.post("/auth/logout")
async def logout(
    authorization: str | None = Header(default=None),
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, str]:
    del user
    if not authorization:
        raise HTTPException(status_code=401, detail="Bearer token is required.")
    token = authorization.removeprefix("Bearer ").strip()
    await _supabase_request("POST", "/logout", token=token)
    return {"message": "Logged out successfully."}



@app.get("/auth/me")
async def read_current_user(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"user": user}

@app.post("/preferences/users")
async def create_preferences(
    preferences: UserPreferences,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid Supabase user.")
    return await _supabase_request(
        "POST",
        "/rest/v1/user_preferences",
        token=user.get("access_token"),
        json={
            "user_id": user_id,
            "preferences": preferences.dict(),
        },
)