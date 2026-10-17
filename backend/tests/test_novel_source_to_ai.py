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


# The review search is restricted to domains listed in .env. Include
# StoryGraph as an additional review source for this test.
review_domains = [
    domain.strip()
    for domain in os.getenv("TAVILY_REVIEW_DOMAINS", "").split(",")
    if domain.strip()
]
if "app.thestorygraph.com" not in review_domains:
    review_domains.append("app.thestorygraph.com")
os.environ["TAVILY_REVIEW_DOMAINS"] = ",".join(review_domains)

# Mock input matching the user's requested form schema.
form = {
    "target_novel": {
        "title": "아몬드",
        "author": "손원평",
        "synopsis": None,
    },
    "user_preferences": {
        "genre_preferences": {
            "liked_genres": ["นิยายแปล", "วรรณกรรมร่วมสมัย"],
            "disliked_genres": ["สยองขวัญ"],
        },
        "favorite_novels": [
            {
                "title": "The Miracles of the Namiya General Store",
                "author": "Keigo Higashino",
                "synopsis": "A Japanese novel about a former general store that receives letters from people seeking advice.",
            }
        ],
        "character_preferences": {
            "liked_traits": ["เห็นอกเห็นใจ", "พัฒนาตัวเอง"],
            "liked_character_description": "ชอบตัวละครที่ค่อย ๆ เรียนรู้ที่จะเข้าใจความรู้สึกของผู้อื่น และเติบโตผ่านความสัมพันธ์",
            "disliked_character_description": "ไม่ชอบตัวละครที่โหดร้ายหรือเอาเปรียบผู้อื่นโดยไม่มีเหตุผล",
        },
        "story_element_preferences": {
            "liked_elements": ["การเติบโตของตัวละคร", "ความสัมพันธ์ในครอบครัว", "การเยียวยาทางใจ"],
            "disliked_elements": ["ความรุนแรงโจ่งแจ้ง", "ตอนจบที่ค้างคา"],
        },
    },
}

# Map the form schema to the preference keys consumed by build_ai_payload.
preferences = form["user_preferences"]
characters = preferences["character_preferences"]
stories = preferences["story_element_preferences"]
user_preference = {
    "liked_genres": preferences["genre_preferences"]["liked_genres"],
    "disliked_genres": preferences["genre_preferences"]["disliked_genres"],
    "character_preferences": (
        [f"Likes: {item}" for item in characters["liked_traits"]]
        + [f"Likes: {characters['liked_character_description']}"]
        + [f"Dislikes: {characters['disliked_character_description']}"]
    ),
    "story_preferences": (
        [f"Likes: {item}" for item in stories["liked_elements"]]
        + [f"Dislikes: {item}" for item in stories["disliked_elements"]]
    ),
    # Keep the favorite novel as user-provided preference evidence. No personal
    # rating was supplied, so rated_novels stays empty rather than inventing one.
    "favorite_novels": preferences["favorite_novels"],
    "rated_novels": [],
}


async def main():
    # ค้น metadata และรีวิวจาก providers จริง
    research = await search_novel(
        form["target_novel"]["title"],
        form["target_novel"]["author"],
        user_provided_description=form["target_novel"]["synopsis"],
        user_provided_source_url=None,
        limit=10,
    )

    if not research.get("metadata"):
        print("ไม่พบ metadata ที่ตรงกับชื่อเรื่องและผู้แต่ง")
        print(json.dumps(research.get("warnings", []), ensure_ascii=False, indent=2))
        return

    # เตรียม input ส่ง AI
    payload = build_ai_payload(research, user_preference)

    print("Metadata provider:", research["metadata"]["provider"])
    print("จำนวนรีวิวที่ผ่านการคัดกรอง:", len(payload["reviews"]))
    print("AI input:", json.dumps(
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
    # Keep the score key explicit in the final JSON output.
    result["match_score"] = analysis.match_score
    result["match_level"] = analysis.match_level

    score = result["match_score"]
    print("คะแนนความเข้ากัน:", f"{score}/100" if score is not None else "ยังคำนวณไม่ได้")
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
