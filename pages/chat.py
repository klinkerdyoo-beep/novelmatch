
import streamlit as st
import base64
from html import escape

from components.navbar import navbar


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Novel Match Results",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/chat.css",
]

for css_file in css_files:
    with open(css_file, encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )


# =========================================================
# Navbar
# =========================================================

navbar()


# =========================================================
# Background
# =========================================================

with open("assets/about-you-bg.png", "rb") as f:
    hero_bg = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <style>
        .stApp {{
            background-image: url("data:image/png;base64,{hero_bg}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Static result-page styles are maintained in style/chat.css.


# =========================================================
# Get User Data
# =========================================================

novel_title = st.session_state.get(
    "novel_title", ""
).strip()

novel_author = st.session_state.get(
    "novel_author", ""
).strip()

novel_synopsis = st.session_state.get(
    "novel_synopsis", ""
).strip()

# The novel form currently collects title, author and synopsis.
# Novel genres should come from a book API when integrated.
novel_genres = st.session_state.get(
    "novel_genres", []
)

favorite_genres = st.session_state.get(
    "favorite_genres", []
)

disliked_genres = st.session_state.get(
    "disliked_genres", []
)

favorite_novels = [
    novel
    for novel in st.session_state.get("favorite_novels", [])
    if novel.get("title", "").strip()
]

enjoy_characters = st.session_state.get(
    "enjoy_characters", []
)

liked_characters = st.session_state.get(
    "liked_characters", ""
)

disliked_character_description = st.session_state.get(
    "disliked_character_description", ""
)

liked_stories = st.session_state.get(
    "liked_stories", []
)

disliked_stories = st.session_state.get(
    "disliked_stories", []
)


# =========================================================
# Demo Result
# Replace with actual AI evaluation later.
# =========================================================

match_score = 86

if match_score >= 80:
    match_status = "Great Match"
    match_status_th = "เข้ากันในระดับสูง"
elif match_score >= 60:
    match_status = "Good Match"
    match_status_th = "เข้ากันในระดับปานกลาง"
else:
    match_status = "Low Match"
    match_status_th = "เข้ากันในระดับต่ำ"

# Gemini uses clearly labeled mock data until its API is connected.
gemini_match_score = 78
if gemini_match_score >= 80:
    gemini_match_status = "Great Match"
    gemini_status_class = "status-high"
elif gemini_match_score >= 60:
    gemini_match_status = "Good Match"
    gemini_status_class = "status-medium"
else:
    gemini_match_status = "Low Match"
    gemini_status_class = "status-low"

if match_score >= 80:
    match_status_class = "status-high"
elif match_score >= 60:
    match_status_class = "status-medium"
else:
    match_status_class = "status-low"

# =========================================================
# Helpers
# =========================================================

def show_section_title(title):
    st.markdown(
        f'<div class="result-section-title">{escape(title)}</div>',
        unsafe_allow_html=True
    )


def show_list(title, items):
    st.markdown(f"**{title}**")

    if items:
        st.write(", ".join(items))
    else:
        st.caption("No preferences provided.")


def show_match_point(title, description, positive=True):
    css_class = "result-positive" if positive else "result-warning"

    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="result-point-title">
                {escape(title)}
            </div>
            <div class="result-point-description">
                {escape(description)}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with st.container(key="result-content"):
    st.markdown(
        """
        <h1>Novel Match Results</h1>
        <div class="result-description">
            Discover how well this novel aligns with your reading preferences.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")


# =========================================================
# Main Glass Card
# =========================================================


with st.container(key="results-glass"):
    # Shared novel information appears once, above both independent model analyses.
    # =========================================================
    # Book Information
    # =========================================================

    with st.container(border=False, key="novel-details-card"):

        show_section_title("Novel Details")

        novel_cover_url = st.session_state.get(
            "novel_cover_url", ""
        )

        cover_col, info_col = st.columns(
            [0.75, 1.5],
            gap="large",
            vertical_alignment="top",
        )

        with cover_col:
            if novel_cover_url:
                st.image(
                    novel_cover_url,
                    use_container_width=True,
                )
            else:
                st.markdown(
                    """
                    <div style="
                        aspect-ratio: 2 / 3;
                        width: 100%;
                        max-width: 180px;
                        margin: 0 auto;
                        border-radius: 12px;
                        background: linear-gradient(
                            145deg, #E4F4F1, #DCE4F5
                        );
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        text-align: center;
                        padding: 12px;
                        box-sizing: border-box;
                        color: #667085;
                    ">
                        <div style="font-size: 36px;">📚</div>
                        <div style="
                            font-size: 13px;
                            margin-top: 10px;
                        ">
                            Book cover unavailable
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with info_col:
            st.markdown(
                f'<div class="result-book-title">'
                f'{escape(novel_title or "Novel title not provided")}'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="result-book-author">'
                f'By {escape(novel_author or "Author not provided")}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Mock data for testing
            mock_genres = ["Fantasy", "Adventure", "Romance"]

            # Use real genres if available; otherwise use mock data
            display_genres = novel_genres or mock_genres

            # Display Genres
            tags_html = "".join(
                f'<span class="result-genre-tag">'
                f'{escape(str(genre))}</span>'
                for genre in display_genres
            )

            st.markdown(tags_html, unsafe_allow_html=True)

            # Display Synopsis
            display_synopsis = (
                novel_synopsis
                or "A fantasy adventure about a hidden kingdom and the people who seek to protect it."
            )

            st.markdown(
                '<div class="result-synopsis-title">Synopsis</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="result-synopsis-text">'
                f'{escape(display_synopsis)}'
                f'</div>',
                unsafe_allow_html=True,
            )


    st.divider()

    # Keep only model-generated analysis in the two side-by-side columns.
    chatgpt_col, gemini_col = st.columns([1, 1], gap="large", vertical_alignment="top")

    with chatgpt_col:
        st.subheader("ChatGPT Analysis")

        # =========================================================
        # Match Score
        # Keep the original score circle design
        # =========================================================

        with st.container(border=False, key="score-card"):

            score_col, summary_col = st.columns(
                [0.75, 1.5],
                gap="large",
                vertical_alignment="center"
            )

            with score_col:
                st.html(
                    f"""
                    <div class="match-score-wrapper">
                        <div
                            class="match-score-circle"
                            style="--score: {match_score * 3.6}deg;"
                        >
                            <div class="match-score-inner">
                                <div class="match-score-number">
                                    {match_score}
                                </div>
                                <div class="match-score-label">
                                    / 100
                                </div>
                            </div>
                        </div>

                        <div class="match-score-text">
                            YOUR MATCH
                        </div>

                        <div class="match-status {match_status_class}">
                            {escape(match_status)}
                        </div>
                    </div>
                    """
                )

            with summary_col:
                st.markdown("### Overall Match Summary")

                st.markdown(
                    """
                    <div class="result-summary">
                        This section explains how well the novel matches
                        your preferred genres, character traits, and
                        storytelling styles.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.caption(
                    "Demo score — replace with the actual evaluation result."
                )

        # =========================================================
        # Match Analysis
        # =========================================================

        with st.container(border=False, key="match-analysis-card"):

            show_section_title("Match Analysis")

            st.markdown(
                "Understand which aspects may fit your preferences "
                "and which ones may not."
            )

            match_col, mismatch_col = st.columns(2, gap="large")

            with match_col:

                st.markdown("### ✓ Matches")

                # Show preference information without claiming
                # that it has already been verified against the novel.
                if favorite_genres:
                    show_match_point(
                        "Your Favorite Genres",
                        "Your preferred genres are: "
                        + ", ".join(favorite_genres)
                        + ". The book's actual genres need to be verified."
                    )
                else:
                    show_match_point(
                        "Genre Preferences",
                        "You have not selected any favorite genres yet."
                    )

                if liked_characters or enjoy_characters:
                    character_summary = ", ".join(liked_characters)

                    if enjoy_characters:
                        character_summary += (
                            (" " if character_summary else "")
                            + enjoy_characters
                        )

                    show_match_point(
                        "Characters You Enjoy",
                        character_summary
                    )
                else:
                    show_match_point(
                        "Character Preferences",
                        "No preferred character traits or description provided."
                    )

                if liked_stories:
                    show_match_point(
                        "Story Elements You Enjoy",
                        ", ".join(liked_stories)
                    )
                else:
                    show_match_point(
                        "Story Preferences",
                        "No preferred story elements selected."
                    )

            with mismatch_col:

                st.markdown("### ⚠ Mismatches")

                if disliked_genres:
                    show_match_point(
                        "Genres You Prefer to Avoid",
                        "Check whether the novel includes: "
                        + ", ".join(disliked_genres)
                        + ". The novel's actual genres need to be verified.",
                        positive=False
                    )
                else:
                    show_match_point(
                        "Genre Mismatches",
                        "No disliked genres provided.",
                        positive=False
                    )

                if disliked_character_description.strip():
                    show_match_point(
                        "Character Traits You Dislike",
                        disliked_character_description,
                        positive=False
                    )
                else:
                    show_match_point(
                        "Character Mismatches",
                        "No disliked character traits provided.",
                        positive=False
                    )

                if disliked_stories:
                    show_match_point(
                        "Story Elements You Prefer to Avoid",
                        ", ".join(disliked_stories),
                        positive=False
                    )
                else:
                    show_match_point(
                        "Story Mismatches",
                        "No disliked story elements selected.",
                        positive=False
                    )


        # =========================================================
        # Review Summary
        # =========================================================

        with st.container(border=False, key="review-summary-card"):

            show_section_title("Review Summary")

            st.markdown(
                "### What do readers say about this novel?"
            )

            st.markdown(
                """
                <div class="result-muted">
                    Review summaries will appear here after review data
                    has been retrieved and analyzed.
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write("")

            review_col1, review_col2, review_col3 = st.columns(3, gap="medium")

            with review_col1:
                st.markdown("#### What Readers Like")
                st.caption(
                    "Highlights from positive reader reviews will appear here."
                )

            with review_col2:
                st.markdown("#### Criticisms")
                st.caption(
                    "Common concerns from reader reviews will appear here."
                )

            with review_col3:
                st.markdown("#### Mixed Opinions")
                st.caption(
                    "Different reader perspectives will appear here."
                )

            st.info(
                "Review data has not been connected yet. "
                "No reader opinions are being presented as verified facts."
            )

        # =========================================================
        # Sources and Limitations
        # =========================================================

        with st.container(border=False, key="source-card"):

            with st.expander(
                "View Sources and Limitations",
                expanded=False
            ):

                st.markdown("### Data Sources")

                st.markdown(
                    """
                    - **Book information:** Google Books API / Open Library API
                    - **Reader reviews:** To be connected
                    - **Preference matching:** NovelMatch evaluation model
                    """
                )

                st.markdown("### Review Data Overview")

                st.write(
                    "Review counts, review excerpts, and source links "
                    "will be displayed after the review retrieval pipeline "
                    "has been implemented."
                )

                st.markdown("### Limitations")

                st.markdown(
                    """
                    - Book metadata may be incomplete or differ between sources.
                    - Reviews may not represent every reader's experience.
                    - The compatibility score depends on the quality and
                    availability of the retrieved information.
                    - The current score and analysis are demonstration content,
                    not a verified prediction.
                    """
                )

                st.markdown("### Review Sources")

                st.caption(
                    "Individual review links will be displayed here "
                    "when real review sources are available."
                )

    with gemini_col:
        st.subheader("Gemini Analysis")

        # Keep the exact same section order and component structure as
        # ChatGPT Analysis. Only the model-specific content differs.

        # =========================================================
        # Match Score
        # =========================================================
        with st.container(border=False, key="gemini-score-card"):
            score_col, summary_col = st.columns(
                [0.75, 1.5],
                gap="large",
                vertical_alignment="center"
            )

            with score_col:
                st.html(
                    """
                    <div class="match-score-wrapper">
                        <div class="match-score-circle" style="--score: 280.8deg;">
                            <div class="match-score-inner">
                                <div class="match-score-number">78</div>
                                <div class="match-score-label">/ 100</div>
                            </div>
                        </div>
                        <div class="match-score-text">GEMINI MATCH</div>
                        <div class="match-status status-medium">Good Match</div>
                    </div>
                    """
                )

            with summary_col:
                st.markdown("### Overall Match Summary")
                st.markdown(
                    """
                    <div class="result-summary">
                        The novel appears to align well with your interest in
                        fantasy and adventure. The character-driven journey is a
                        likely strength, while the romance element may be less
                        prominent than your preferences suggest.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.caption(
                    "Illustrative mock data for UI testing — not generated by the Gemini API."
                )

        # =========================================================
        # Match Analysis
        # =========================================================
        with st.container(border=False, key="gemini-match-analysis-card"):
            show_section_title("Match Analysis")
            st.markdown(
                "Understand which aspects may fit your preferences "
                "and which ones may not."
            )

            match_col, mismatch_col = st.columns(2, gap="large")

            with match_col:
                st.markdown("### ✓ Matches")
                show_match_point(
                    "Genre Preferences",
                    "You have not selected any favorite genres yet."
                )
                show_match_point(
                    "Character Preferences",
                    "No preferred character traits or description provided."
                )
                show_match_point(
                    "Story Preferences",
                    "No preferred story elements selected."
                )

            with mismatch_col:
                st.markdown("### ⚠ Mismatches")
                show_match_point(
                    "Genre Mismatches",
                    "No disliked genres provided.",
                    positive=False
                )
                show_match_point(
                    "Character Mismatches",
                    "No disliked character traits provided.",
                    positive=False
                )
                show_match_point(
                    "Story Mismatches",
                    "No disliked story elements selected.",
                    positive=False
                )

        # =========================================================
        # Review Summary
        # =========================================================
        with st.container(border=False, key="gemini-review-summary-card"):
            show_section_title("Review Summary")
            st.markdown("### What do readers say about this novel?")
            st.markdown(
                """
                <div class="result-muted">
                    Example review themes are shown below for layout preview only.
                    They are not based on retrieved reader reviews.
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write("")

            review_col1, review_col2, review_col3 = st.columns(3, gap="medium")
            with review_col1:
                st.markdown("#### What Readers Like")
                st.caption("Readers may enjoy the imaginative setting and sense of adventure (mock example).")
            with review_col2:
                st.markdown("#### Criticisms")
                st.caption("Some readers may want deeper character development (mock example).")
            with review_col3:
                st.markdown("#### Mixed Opinions")
                st.caption("Opinions may differ on how much romance the story contains (mock example).")

            st.info(
                "Mockup content only. Gemini API and verified reader-review sources are not connected."
            )

        # =========================================================
        # Sources and Limitations
        # =========================================================
        with st.container(border=False, key="gemini-source-card"):
            with st.expander("View Sources and Limitations", expanded=False):
                st.markdown("### Data Sources")
                st.markdown(
                    """
                    - **Book information:** Google Books API / Open Library API
                    - **Reader reviews:** To be connected
                    - **AI analysis:** Illustrative mock data; Gemini API not connected yet
                    """
                )

                st.markdown("### Review Data Overview")
                st.write(
                    "Review counts, review excerpts, and source links will be "
                    "displayed after the review retrieval pipeline has been implemented."
                )

                st.markdown("### Limitations")
                st.markdown(
                    """
                    - The displayed Gemini score and analysis are mock data, not model-generated results.
                    - Book metadata may be incomplete or differ between sources.
                    - Reviews may not represent every reader's experience.
                    - Results depend on the quality of the information and prompt supplied to the model.
                    """
                )

                st.markdown("### Review Sources")
                st.caption(
                    "Individual review links will be displayed here when real review sources are available."
                )


    # Full-width navigation belongs below both model panels, not inside ChatGPT.
    st.divider()
    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        if st.button(
            "← Back to Home",
            use_container_width=True,
            key="result_back_to_home"
        ):
            st.switch_page("main.py")
