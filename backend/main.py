import os
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine
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

app = FastAPI()


class AnalysisRequest(BaseModel):
    # Preferred contract: the nested form schema handled by user_input.py.
    target_novel: dict[str, Any] | None = None
    user_preferences: dict[str, Any] | None = None

    # Keep the existing flattened API contract for existing callers.
    title: str | None = Field(default=None, min_length=1, max_length=300)
    author: str | None = Field(default=None, min_length=1, max_length=300)
    synopsis: str | None = Field(default=None, max_length=20000)
    source_url: str | None = None
    user_preference: dict[str, Any] | None = None
    provider: Literal["gemini", "gpt_oss"] = "gemini"


@app.post("/analysis")
async def analyze_novel(request: AnalysisRequest) -> dict[str, Any]:
    """Search for novel evidence and return a validated AI analysis."""

    try:
        if request.target_novel is not None or request.user_preferences is not None:
            if request.target_novel is None or request.user_preferences is None:
                raise ValueError("target_novel and user_preferences must be provided together")
            target, user_preference = normalize_user_input({
                "target_novel": request.target_novel,
                "user_preferences": request.user_preferences,
            })
            title = target["title"]
            author = target["author"]
            synopsis = target["synopsis"] or None
            source_url = None
        else:
            if not request.title or not request.author or request.user_preference is None:
                raise ValueError(
                    "provide either target_novel/user_preferences or title/author/user_preference"
                )
            title = request.title
            author = request.author
            synopsis = request.synopsis
            source_url = request.source_url
            user_preference = request.user_preference

        research = await NovelResearchService().search(
            title,
            author,
            user_provided_description=synopsis,
            user_provided_source_url=source_url,
        )
        payload = build_ai_payload(research, user_preference)
        analysis = (
            GeminiAIService().analyze(**payload)
            if request.provider == "gemini"
            else _analyze_with_gpt_oss(payload)
        )
        output = analysis.model_dump()
        validate_analysis_evidence(output, payload)
        return merge_analysis_limitations(output, payload)
    except InsufficientNovelDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except GeminiRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except (GeminiAPIError, GeminiInvalidResponseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GeminiServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GPTOSSConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GPTOSSTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except GPTOSSRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GPTOSSInvalidResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GPTOSSAPIError as exc:
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


# @app.get("/supabase-check")
# async def supabase_check() -> dict[str, object]:
#     try:
#         async with engine.connect() as connection:
#             result = await connection.execute(text("SELECT 1"))
#             return {
#                 "connected": result.scalar_one() == 1,
#                 "message": "Supabase database connection is working",
#             }
#     except SQLAlchemyError as exc:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Supabase database connection failed: {exc}",
#         ) from exc
