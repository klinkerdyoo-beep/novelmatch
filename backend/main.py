import logging
from pathlib import Path
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from postgrest.exceptions import APIError
from supabase import Client, create_client

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from services.novel_sources import (
    InsufficientNovelDataError,
    NovelResearchService,
    build_ai_payload,
    merge_analysis_limitations,
)
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field
from services.gemini_service import (
    GeminiAIService,
    GeminiAPIError,
    GeminiConfigurationError,
    GeminiInvalidResponseError,
    GeminiRateLimitError,
    GeminiServiceError,
    GeminiTimeoutError,
    MASTER_ANALYSIS_PROMPT,
    MatchAnalysis,
)
from services.gpt_oss_service import (
    GPTOSSAPIError,
    GPTOSSConfigurationError,
    GPTOSSInvalidResponseError,
    GPTOSSRateLimitError,
    GPTOSSService,
    GPTOSSTimeoutError,
)
from services.novel_sources import (
    InsufficientNovelDataError,
    NovelResearchService,
    build_ai_payload,
    merge_analysis_limitations,
    normalize_user_input,
    validate_analysis_evidence,
)
import asyncio

app = FastAPI(title="NovelMatch API", version="1.0.0")
bearer_scheme = HTTPBearer()

supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_ANON_KEY"],
)


class NovelInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    author: str = Field(min_length=1, max_length=300)
    synopsis: str | None = Field(default=None, max_length=20000)
    book_cover: str | None = None
    genre: list[str] = Field(default_factory=list)


class GenrePreferences(BaseModel):
    enjoyed_genres: list[str] = Field(default_factory=list)
    disliked_genres: list[str] = Field(default_factory=list)


class CharacterPreferences(BaseModel):
    enjoyed_character: list[str] = Field(default_factory=list)
    liked_character: str = ""
    disliked_character: str = ""


class StoryPreferences(BaseModel):
    liked_story: list[str] = Field(default_factory=list)
    disliked_story: list[str] = Field(default_factory=list)


class UserPreferences(BaseModel):
    genre_preferences: GenrePreferences = Field(default_factory=GenrePreferences)
    character_preferences: CharacterPreferences = Field(default_factory=CharacterPreferences)
    story_element_preferences: StoryPreferences = Field(default_factory=StoryPreferences)


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
    if token:
        headers["Authorization"] = "Bearer " + token
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
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Bearer token is required.")

    token = credentials.credentials
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
    user["_access_token"] = token
    return user

class AnalysisRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300, description="ชื่อนิยาย")
    author: str = Field(min_length=1, max_length=300, description="ชื่อผู้แต่ง")
    synopsis: str | None = Field(default=None, max_length=20000, description="เรื่องย่อ")
    book_cover: str | None = Field(default=None, description="URL รูปปก")
    genre: list[str] = Field(default_factory=list, description="หมวดหมู่นิยาย")
    # provider: Literal["gemini", "gpt_oss"]
@app.get("/history")
async def get_user_match_history(user: dict[str, Any] = Depends(require_user)):
    user_id = user.get("id")
    supabase.postgrest.auth(user["_access_token"])
    
    try:
        res = (
            supabase.table("match_history")
            .select("*")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .execute()
        )
        records = res.data or []
    except Exception as exc:
        logger.error("Error querying match_history: %s", exc)
        records = []

    novel_ids = list({r["novel_id"] for r in records if r.get("novel_id") is not None})
    novel_map = {}
    if novel_ids:
        try:
            novels_res = (
                supabase.table("comparison_novels")
                .select("id,title,author,book_cover,synopsis,genre")
                .in_("id", novel_ids)
                .execute()
            )
            for n in (novels_res.data or []):
                novel_map[n["id"]] = n
        except Exception as exc:
            logger.error("Error querying comparison_novels: %s", exc)

    grouped = {}
    for r in records:
        nid = r.get("novel_id")
        novel_info = novel_map.get(nid, {})
        if nid not in grouped:
            grouped[nid] = {
                "id": nid,
                "title": novel_info.get("title", "Untitled"),
                "author": novel_info.get("author", "Unknown"),
                "cover_url": novel_info.get("book_cover", ""),
                "synopsis": novel_info.get("synopsis", ""),
                "genres": novel_info.get("genre") or [],
                "chatgpt": None,
                "gemini": None,
            }
        

        summary_tag = str(r.get("matches_summary") or "")
        cleaned_summary = (r.get("review_overview") or summary_tag).replace("[GPT-OSS] ", "").replace("[Gemini] ", "")
        model_data = {
            "score": r.get("score"),
            "status": r.get("matches_level"),
            "overall_summary": cleaned_summary,
            "matches": r.get("matches") or [],
            "mismatches": r.get("mismatches") or [],
            "review_summary": r.get("review_summary") or {},
            "sources": r.get("data_sources") or [],
            "limitations": r.get("limitations") or [],
        }
        if "[GPT-OSS]" in summary_tag or "gpt" in summary_tag.lower():
            if grouped[nid]["chatgpt"] is None or (grouped[nid]["chatgpt"].get("score") is None and model_data.get("score") is not None):
                grouped[nid]["chatgpt"] = model_data
        else:
            if grouped[nid]["gemini"] is None or (grouped[nid]["gemini"].get("score") is None and model_data.get("score") is not None):
                grouped[nid]["gemini"] = model_data

    return {"data": list(grouped.values())}

    

# --- Endpoint /analysis ---
@app.post("/analysis")
async def analyze_novel(
    request: AnalysisRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    supabase.postgrest.auth(user["_access_token"])
    try:

        pref_res = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
        if not pref_res.data:
            raise HTTPException(
                status_code=400,
                detail="ยังไม่พบข้อมูลความชอบในระบบ กรุณาตั้งค่าที่ /preferences ก่อนเริ่มวิเคราะห์",
            )
        pref_row = pref_res.data[0]

        char_prefs = list(pref_row.get("enjoyed_character") or [])
        if pref_row.get("liked_character"):
            char_prefs.append(f"Likes: {pref_row['liked_character']}")
        if pref_row.get("disliked_character"):
            char_prefs.append(f"Dislikes: {pref_row['disliked_character']}")

        story_prefs = [f"Likes: {s}" for s in (pref_row.get("enjoyed_story") or [])]
        story_prefs += [f"Dislikes: {s}" for s in (pref_row.get("disliked_story") or [])]

        user_preference_payload = {
            "liked_genres": pref_row.get("enjoyed_genres") or [],
            "disliked_genres": pref_row.get("disliked_genres") or [],
            "character_preferences": char_prefs,
            "story_preferences": story_prefs,
            "rated_novels": [],
        }

        research = await NovelResearchService().search(
            title=request.title,
            author=request.author,
            user_provided_description=request.synopsis,
            user_provided_source_url=None,
        )
        payload = build_ai_payload(research, user_preference_payload)

        gemini_task = asyncio.to_thread(GeminiAIService().analyze, **payload)
        gpt_oss_task = asyncio.to_thread(_analyze_with_gpt_oss, payload)

        gemini_res, gpt_res = await asyncio.gather(
            gemini_task, gpt_oss_task, return_exceptions=True
        )

        if isinstance(gemini_res, Exception):
            raise gemini_res

        gemini_output = gemini_res.model_dump()
        validate_analysis_evidence(gemini_output, payload)
        final_gemini = merge_analysis_limitations(gemini_output, payload)
        final_gpt = None

        if not isinstance(gpt_res, Exception):
            try:
                gpt_output = gpt_res.model_dump()
                validate_analysis_evidence(gpt_output, payload)
                final_gpt = merge_analysis_limitations(gpt_output, payload)
            except Exception as exc:
                logger.warning("Error processing GPT-OSS output: %s", exc)
                final_gpt = None
        else:
            logger.warning("GPT-OSS model failed or timed out (504): %s", gpt_res)

        novel_res = (
            supabase.table("comparison_novels")
            .select("id")
            .eq("title", request.title)
            .eq("author", request.author)
            .limit(1)
            .execute()
        )
        meta = research.metadata if hasattr(research, "metadata") else (research.get("metadata") if isinstance(research, dict) else None)
        meta_genres = (getattr(meta, "genres", None) if not isinstance(meta, dict) else meta.get("genres")) or []
        meta_cover = getattr(meta, "cover_url", None) if not isinstance(meta, dict) else meta.get("cover_url")

        if novel_res.data:
            novel_id = novel_res.data[0]["id"]
        else:
            novel_insert = (
                supabase.table("comparison_novels")
                .insert({
                    "title": request.title,
                    "author": request.author,
                    "synopsis": request.synopsis,
                    "genre": request.genre or meta_genres,
                    "book_cover": request.book_cover or meta_cover,
                })
                .execute()
            )
            novel_id = novel_insert.data[0]["id"]

        gemini_record = {
            "user_id": user_id,
            "novel_id": novel_id,
            "score": final_gemini.get("match_score"),
            "matches": final_gemini.get("matches", []),
            "mismatches": final_gemini.get("mismatches", []),
            "limitations": final_gemini.get("limitations", []),
            "matches_level": final_gemini.get("match_level"),
            "matches_summary": f"[Gemini] {final_gemini.get('summary', '')}",
            "data_sources": final_gemini.get("sources", []),
            "review_summary": final_gemini.get("review_summary", {}),
            "review_overview": final_gemini.get("summary"),
            "review_sources": [
                s for s in final_gemini.get("sources", [])
                if "review" in str(s.get("evidence_id", ""))
            ],
        }

        records_to_insert = [gemini_record]

        if final_gpt:
            gpt_record = {
                "user_id": user_id,
                "novel_id": novel_id,
                "score": final_gpt.get("match_score"),
                "matches": final_gpt.get("matches", []),
                "mismatches": final_gpt.get("mismatches", []),
                "limitations": final_gpt.get("limitations", []),
                "matches_level": final_gpt.get("match_level"),
                "matches_summary": f"[GPT-OSS] {final_gpt.get('summary', '')}",
                "data_sources": final_gpt.get("sources", []),
                "review_summary": final_gpt.get("review_summary", {}),
                "review_overview": final_gpt.get("summary"),
                "review_sources": [
                    s for s in final_gpt.get("sources", [])
                    if "review" in str(s.get("evidence_id", ""))
                ],
            }
            records_to_insert.append(gpt_record)
    
        history_res = supabase.table("match_history").insert(records_to_insert).execute()

        return {
            "match_history_ids": [row["id"] for row in (history_res.data or [])],
            "novel_id": novel_id,
            "novel_title": request.title,
            "book_cover": request.book_cover or meta_cover,
            "cover_url": request.book_cover or meta_cover,
            "results": {
                "gemini": final_gemini,
                "gpt_oss": final_gpt,
            },
        }
    except APIError as exc:
        raise HTTPException(status_code=400, detail=exc.message or "Database error.") from exc
    except InsufficientNovelDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (GeminiConfigurationError, GPTOSSConfigurationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (GeminiTimeoutError, GPTOSSTimeoutError) as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except (GeminiRateLimitError, GPTOSSRateLimitError) as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except (
        GeminiAPIError,
        GeminiInvalidResponseError,
        GeminiServiceError,
        GPTOSSInvalidResponseError,
        GPTOSSAPIError,
    ) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

def _analyze_with_gpt_oss(payload: dict[str, Any]) -> MatchAnalysis:
    """Compatibility entry point delegating GPT-OSS analysis to its service."""
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("GPT_OSS_API_KEY")
    base_url = os.getenv("GPT_OSS_BASE_URL")
    model = os.getenv("GPT_OSS_MODEL")
    missing = [
        name for name, value in (
            ("NVIDIA_API_KEY or GPT_OSS_API_KEY", api_key),
            ("GPT_OSS_BASE_URL", base_url),
            ("GPT_OSS_MODEL", model),
        ) if not value
    ]
    if missing:
        raise GPTOSSConfigurationError(
            "GPT-OSS configuration is missing: " + ", ".join(missing)
        )
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=GPTOSSService._build_timeout(None, None),
        max_retries=0,
    )
    return GPTOSSService(client=client, model=model).analyze(**payload)

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
    identifier = request.email.strip()
    target_email = identifier

    # If identifier is not an email (does not contain '@'), look up email from public.users
    if "@" not in identifier:
        try:
            res = (
                supabase.table("users")
                .select("email")
                .ilike("username", identifier)
                .execute()
            )
            if res.data and res.data[0].get("email"):
                target_email = res.data[0]["email"]
            else:
                raise HTTPException(status_code=400, detail="Invalid username or password.")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not resolve username.") from exc

    return await _supabase_request(
        "POST",
        "/token?grant_type=password",
        json={"email": target_email, "password": request.password},
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
async def read_current_user(
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
  user_id = user.get("id")

  # Query ตาราง public.users ด้วย id
  res = (
      supabase.table("users")
      .select("username")
      .eq("id", user_id)
      .execute()
      .data
  )

  username = res[0].get("username") if res else "User"

  return {
      "user": {
          "id": user_id,
          "email": user.get("email"),
          "username": username,
      }
  }
  
@app.get("/novels")
async def get_novels(
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    supabase.postgrest.auth(user["_access_token"])
    user_id = user.get("id")
    if user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="You can only read your own novels.")
    try:
        response = (
            supabase.table("comparison_novels")
            .select("id,title,synopsis,author,genre,book_cover")
            .order("id", desc=True)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=400,
            detail=exc.message or "Supabase could not read novels.",
        ) from exc
    return {"data": response.data}


@app.get("/novels/{novel_id}")
async def get_novel(
    novel_id: str,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    supabase.postgrest.auth(user["_access_token"])
    try:
        response = (
            supabase.table("comparison_novels")
            .select("id,title,synopsis,author,genre,book_cover")
            .eq("id", novel_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=400,
            detail=exc.message or "Supabase could not read the novel.",
        ) from exc
    if not response.data:
        raise HTTPException(status_code=404, detail="Novel not found.")
    return {"data": response.data[0]}




@app.post("/novels")
async def create_novel(
    novel: NovelInput,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    if not novel.title or not novel.author:
        raise HTTPException(status_code=422, detail="Title and author are required.")
    
    if user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="You can only create novels for your own account.")
    supabase.postgrest.auth(user["_access_token"])
    try:
        response = (
            supabase.table("comparison_novels")
            .upsert(novel.model_dump())
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=400,
            detail=exc.message or "Supabase could not create the novel.",
        ) from exc
    return {"data": response.data}

@app.post("/preferences")
async def create_preferences(
    preferences: UserPreferences,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    if user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="You can only update your own preferences.")

    supabase.postgrest.auth(user["_access_token"])
    try:
        response = (
            supabase.table("user_preferences")
            .upsert(
                {
                    "user_id": user_id,
                    "enjoyed_character": preferences.character_preferences.enjoyed_character,
                    "disliked_character": preferences.character_preferences.disliked_character,
                    "liked_character": preferences.character_preferences.liked_character,
                    "enjoyed_story": preferences.story_element_preferences.liked_story,
                    "disliked_story": preferences.story_element_preferences.disliked_story,
                    "enjoyed_genres": preferences.genre_preferences.enjoyed_genres,
                    "disliked_genres": preferences.genre_preferences.disliked_genres,
                },
                on_conflict="user_id",
            )
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=400,
            detail=exc.message or "Supabase could not save user preferences.",
        ) from exc
    return {"data": response.data}



@app.get("/preferences")
async def get_preferences(
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    if user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="You can only read your own preferences.")

    supabase.postgrest.auth(user["_access_token"])
    try:
        response = (
            supabase.table("user_preferences")
            .select(
                "enjoyed_character,disliked_character,liked_character,"
                "enjoyed_story,disliked_story,enjoyed_genres,disliked_genres"
            )
            .eq("user_id", user_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=400,
            detail=exc.message or "Supabase could not read user preferences.",
        ) from exc
    if not response.data:
        raise HTTPException(status_code=404, detail="User preferences not found.")
    row = response.data[0]
    return {
        "preferences": {
            "genre_preferences": {
                "enjoyed_genres": row.get("enjoyed_genres", []),
                "disliked_genres": row.get("disliked_genres", []),
            },
            "character_preferences": {
                "enjoyed_character": row.get("enjoyed_character", []),
                "liked_character": row.get("liked_character", ""),
                "disliked_character": row.get("disliked_character", ""),
            },
            "story_element_preferences": {
                "liked_story": row.get("enjoyed_story", []),
                "disliked_story": row.get("disliked_story", []),
            },
        }
    }