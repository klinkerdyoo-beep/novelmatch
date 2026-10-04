from services.gemini_service import GeminiAIService


def main():
    service = GeminiAIService()

    user_preference = {
        "liked_genres": ["Fantasy", "Adventure"],
        "disliked_genres": ["Horror"],
        "character_preferences": [
            "Strong and independent protagonist"
        ],
        "story_preferences": [
            "Adventure",
            "World-building",
            "Fast-paced story"
        ],
        "rated_novels": [
            {
                "title": "The Hobbit",
                "rating": 5
            }
        ],
    }

    novel = {
        "title": "A Wizard of Earthsea",
        "author": "Ursula K. Le Guin",
        "genres": ["Fantasy", "Adventure"],
        "description": (
            "A young wizard learns to control his powers "
            "while facing a dangerous shadow."
        ),
        "publisher": "Parnassus Press",
        "published_date": "1968",
        "rating": 4.2,
        "rating_count": 100000,
    }

    reviews = [
        {
            "review_id": "test-review-1",
            "text": (
                "The world-building is excellent and the story "
                "has a strong coming-of-age adventure."
            ),
            "rating": 5,
            "source": "Test",
            "url": "https://example.com/review/1",
        },
        {
            "review_id": "test-review-2",
            "text": (
                "The pacing is slower than I expected, "
                "but the characters are interesting."
            ),
            "rating": 4,
            "source": "Test",
            "url": "https://example.com/review/2",
        },
    ]

    result = service.analyze(
        user_preference=user_preference,
        novel=novel,
        reviews=reviews,
    )

    print("\n=== NovelMatch Gemini Test ===")
    print("match_score:", result.match_score)
    print("match_level:", result.match_level)
    print("matches:", result.matches)
    print("mismatches:", result.mismatches)
    print("review_summary:", result.review_summary)
    print("sources:", result.sources)
    print("limitations:", result.limitations)


if __name__ == "__main__":
    main()
