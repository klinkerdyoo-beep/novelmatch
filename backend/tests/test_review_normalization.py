from backend.services.novel_sources.models import ReviewSource
from backend.services.novel_sources.normalization import normalize_reviews


def test_exact_title_review_without_author_in_snippet_is_retained():
    candidate = ReviewSource(
        title="The Hobbit Book Review",
        url="https://app.thestorygraph.com/reviews/example",
        snippet=(
            "A reader review of The Hobbit: the adventure is delightful, "
            "and the pacing feels lively throughout the story."
        ),
        source_name="app.thestorygraph.com",
        relevance_score=0.91,
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert len(accepted) == 1
    assert accepted[0].review_id.startswith("review-")
    assert accepted[0].verification_status == "heuristic_only"
    assert any("did not independently confirm the author" in warning for warning in warnings)


def test_review_filter_warning_reports_rejection_reason():
    candidate = ReviewSource(
        title="Another Book Review",
        url="https://app.thestorygraph.com/reviews/example",
        snippet="A reader review with enough text to make the rejection reason clear.",
    )

    accepted, warnings = normalize_reviews([candidate], "The Hobbit", "J.R.R. Tolkien")

    assert accepted == []
    assert any("1 title mismatch" in warning for warning in warnings)
