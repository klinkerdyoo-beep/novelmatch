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


# class AnalysisRequest(BaseModel):
#     target_novel: NovelInput
#     user_preferences: UserPreferences


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


# --- Endpoint /analysis ---
@app.post("/analysis")
async def analyze_novel(
    request: AnalysisRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    
    
    try:
        # Step 1: ดึง Preference ของ User จาก Database อัตโนมัติ
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

        # Step 2: ให้ AI ค้นคว้าและคำนวณผลการจับคู่
        research = await NovelResearchService().search(
            title=request.title,
            author=request.author,
            user_provided_description=request.synopsis,
            user_provided_source_url=None,
        )
        payload = build_ai_payload(research, user_preference_payload)

        # 3. รันทั้ง 2 โมเดลแบบขนาน (Parallel Execution) พร้อมกัน
        # gemini_task = asyncio.to_thread(GeminiAIService().analyze, **payload)
        gpt_oss_task = asyncio.to_thread(_analyze_with_gpt_oss, payload)

        # gemini_raw, gpt_raw = await asyncio.gather(gemini_task, gpt_oss_task)
        gpt_raw = await asyncio.gather(gpt_oss_task)

        # 4. ตรวจสอบและจัดการผลลัพธ์ของแต่ละโมเดล
        # ประมวลผลผลลัพธ์ของ Gemini
        # gemini_output = gemini_raw.model_dump()
        # validate_analysis_evidence(gemini_output, payload)
        # final_gemini = merge_analysis_limitations(gemini_output, payload)

        # ประมวลผลผลลัพธ์ของ GPT-OSS
        gpt_output = gpt_raw.model_dump()
        validate_analysis_evidence(gpt_output, payload)
        final_gpt = merge_analysis_limitations(gpt_output, payload)

        # Step 3: บันทึกนิยายลงตาราง comparison_novels (ถ้ามีแล้วใช้ของเดิม ถ้ายังไม่มีให้สร้างใหม่)
        novel_res = (
            supabase.table("comparison_novels")
            .select("id")
            .eq("title", request.title)
            .eq("author", request.author)
            .limit(1)
            .execute()
        )
        if novel_res.data:
            novel_id = novel_res.data[0]["id"]
        else:
            novel_insert = (
                supabase.table("comparison_novels")
                .insert({
                    "title": request.title,
                    "author": request.author,
                    "synopsis": request.synopsis,
                    "genre": request.genre or research.get("metadata", {}).get("genres", []),
                    "book_cover": request.book_cover or research.get("metadata", {}).get("cover_url"),
                })
                .execute()
            )
            novel_id = novel_insert.data[0]["id"]

        # Step 4: บันทึกผลลัพธ์ลงตาราง match_history
        # gemini_record = {
        #     "user_id": user_id,
        #     "novel_id": novel_id,
        #     "score": final_gemini.get("match_score"),
        #     "matches": final_gemini.get("matches", []),
        #     "mismatches": final_gemini.get("mismatches", []),
        #     "limitations": final_gemini.get("limitations", []),
        #     "matches_level": final_gemini.get("match_level"),
        #     "matches_summary": f"[Gemini] {final_gemini.get('summary', '')}",
        #     "data_sources": final_gemini.get("sources", []),
        #     "review_summary": final_gemini.get("review_summary", {}),
        #     "review_overview": final_gemini.get("summary"),
        #     "review_sources": [
        #         s for s in final_gemini.get("sources", [])
        #         if "review" in str(s.get("evidence_id", ""))
        #     ],
        # }

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
        history_res = supabase.table("match_history").insert(gpt_record).execute()
        # history_res = supabase.table("match_history").insert([gemini_record, gpt_record]).execute()

        # ส่ง ID ทั้ง 2 แถวและผลการวิเคราะห์กลับให้ Frontend
        return {
            "match_history_ids": [row["id"] for row in (history_res.data or [])],
            "novel_id": novel_id,
            "novel_title": request.title,
            "results": {
                # "gemini": final_gemini,
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
# async def analyze_novel(request: AnalysisRequest) -> dict[str, Any]:
#     """Search for novel evidence and return a validated AI analysis."""

#     try:
#         if request.target_novel is not None or request.user_preferences is not None:
#             if request.target_novel is None or request.user_preferences is None:
#                 raise ValueError("target_novel and user_preferences must be provided together")
#             target, user_preference = normalize_user_input({
#                 "target_novel": request.target_novel,
#                 "user_preferences": request.user_preferences,
#             })
#             title = target["title"]
#             author = target["author"]
#             synopsis = target["synopsis"] or None
#             source_url = None
#         else:
#             if not request.title or not request.author or request.user_preference is None:
#                 raise ValueError(
#                     "provide either target_novel/user_preferences or title/author/user_preference"
#                 )
#             title = request.title
#             author = request.author
#             synopsis = request.synopsis
#             source_url = request.source_url
#             user_preference = request.user_preference

#         research = await NovelResearchService().search(
#             title,
#             author,
#             user_provided_description=synopsis,
#             user_provided_source_url=source_url,
#         )
#         payload = build_ai_payload(research, user_preference)
#         analysis = (
#             GeminiAIService().analyze(**payload)
#             if request.provider == "gemini"
#             else _analyze_with_gpt_oss(payload)
#         )
#         output = analysis.model_dump()
#         validate_analysis_evidence(output, payload)
#         return merge_analysis_limitations(output, payload)
#     except InsufficientNovelDataError as exc:
#         raise HTTPException(status_code=422, detail=str(exc)) from exc
#     except GeminiConfigurationError as exc:
#         raise HTTPException(status_code=503, detail=str(exc)) from exc
#     except GeminiTimeoutError as exc:
#         raise HTTPException(status_code=504, detail=str(exc)) from exc
#     except GeminiRateLimitError as exc:
#         raise HTTPException(status_code=429, detail=str(exc)) from exc
#     except (GeminiAPIError, GeminiInvalidResponseError) as exc:
#         raise HTTPException(status_code=502, detail=str(exc)) from exc
#     except GeminiServiceError as exc:
#         raise HTTPException(status_code=502, detail=str(exc)) from exc
#     except GPTOSSConfigurationError as exc:
#         raise HTTPException(status_code=503, detail=str(exc)) from exc
#     except GPTOSSTimeoutError as exc:
#         raise HTTPException(status_code=504, detail=str(exc)) from exc
#     except GPTOSSRateLimitError as exc:
#         raise HTTPException(status_code=429, detail=str(exc)) from exc
#     except GPTOSSInvalidResponseError as exc:
#         raise HTTPException(status_code=502, detail=str(exc)) from exc
#     except GPTOSSAPIError as exc:
#         raise HTTPException(status_code=502, detail=str(exc)) from exc
#     except ValueError as exc:
#         raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    return {"user": {key: value for key, value in user.items() if key != "_access_token"}}

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