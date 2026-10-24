"""Run one NovelMatch JSON testcase without starting the FastAPI server."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

# from services.gemini_service import GeminiAIService
from services.gpt_oss_service import GPTOSSService
from services.novel_sources import (
    NovelResearchService,
    build_ai_payload,
    normalize_user_input,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


async def run(testcase_path: Path) -> dict:
    with testcase_path.open(encoding="utf-8") as file:
        user_input = json.load(file)

    target, preferences = normalize_user_input(user_input)
    research = await NovelResearchService().search(
        target["title"],
        target["author"],
        user_provided_description=target["synopsis"] or None,
    )

    if research.metadata is None:
        raise RuntimeError(
            "ไม่พบข้อมูลหนังสือที่ตรงกัน:\n"
            + "\n".join(research.warnings)
        )

    payload = build_ai_payload(research, preferences)
    # gemini_analysis = GeminiAIService().analyze(**payload)
    gpt_analysis = GPTOSSService().analyze(**payload)
    research_data = research.to_dict()
    return {
        "input": user_input,
        "research": {
            "metadata": research_data["metadata"],
            "reviews": research_data["reviews"],
            "warnings": research_data["warnings"],
        },
        "ai_payload": payload,
        # "gemini_analysis": gemini_analysis.model_dump(mode="json"),
        "gpt_analysis": gpt_analysis.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("testcase", type=Path, help="Path to the testcase JSON file")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation_results.json",
        help="Path for the JSON output",
    )
    args = parser.parse_args()

    result = asyncio.run(run(args.testcase))
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(f"\nบันทึกผลลัพธ์แล้ว: {args.output}")


if __name__ == "__main__":
    main()
