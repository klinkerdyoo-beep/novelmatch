import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from services.gemini_service import GeminiAIService, GeminiServiceError
from services.novel_sources import (
    build_ai_payload,
    merge_analysis_limitations,
    search_novel,
)


# จำลองค่าที่ผู้ใช้กรอกจากหน้า Frontend
form = {
    "novel_title": "The Hobbit",
    "novel_author": "J. R. R. Tolkien",
    "novel_synopsis": "",
    "favorite_genres": ["Fantasy", "Adventure"],
    "disliked_genres": ["Horror"],
    "liked_characters": ["Strong", "Independent"],
    "disliked_characters": ["Mysterious"],
    "liked_stories": ["Complex story"],
    "disliked_stories": ["Slow-paced"],
}

# แปลงค่าฟอร์มเป็น user_preference ตาม schema ของ AI
# Frontend ปัจจุบันเก็บ favorite novels แค่ชื่อ จึงยังใส่ rated_novels ว่างไว้
user_preference = {
    "liked_genres": form["favorite_genres"],
    "disliked_genres": form["disliked_genres"],
    "character_preferences": (
        [f"Likes: {item}" for item in form["liked_characters"]]
        + [f"Dislikes: {item}" for item in form["disliked_characters"]]
    ),
    "story_preferences": (
        [f"Likes: {item}" for item in form["liked_stories"]]
        + [f"Dislikes: {item}" for item in form["disliked_stories"]]
    ),
    "rated_novels": [],
}


async def main():
    # ค้น metadata และรีวิวจาก providers จริง
    research = await search_novel(
        form["novel_title"],
        form["novel_author"],
        user_provided_description=form["novel_synopsis"] or None,
        limit=3,
    )

    if not research.get("metadata"):
        print("ไม่พบ metadata ที่ตรงกับชื่อเรื่องและผู้แต่ง")
        print(json.dumps(research.get("warnings", []), ensure_ascii=False, indent=2))
        return

    # เตรียม input ส่ง AI
    payload = build_ai_payload(research, user_preference)

    print("Metadata provider:", research["metadata"]["provider"])
    print("จำนวนรีวิวที่ผ่านการคัดกรอง:", len(payload["reviews"]))
    print("AI input ตาม schema:", json.dumps(
        payload, ensure_ascii=False, indent=2
    ))
    print("คำเตือนจากการค้น:", json.dumps(
        research.get("warnings", []), ensure_ascii=False, indent=2
    ))
    print("ส่งข้อมูลให้ Gemini...")

    try:
        analysis = GeminiAIService().analyze(**payload)
    except GeminiServiceError as error:
        print(f"Gemini เรียกไม่สำเร็จ: {error}")
        return

    # Search limitations are added to the final result, not sent as extra
    # fields inside the agreed AI input schema.
    result = merge_analysis_limitations(
        analysis.model_dump(mode="json"),
        payload,
        research.get("warnings", []),
    )

    print("ผลวิเคราะห์จาก Gemini:")
    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    required_keys = ["GEMINI_API_KEY"]
    missing = [key for key in required_keys if not os.getenv(key)]
    if missing:
        raise SystemExit(
            "ยังไม่ได้ตั้งค่าใน .env: " + ", ".join(missing)
        )

    asyncio.run(main())
