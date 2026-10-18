
import streamlit as st
import base64
from html import escape

from components.navbar import navbar


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="My Reading History",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/history.css",
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
    unsafe_allow_html=True
)


# =========================================================
# Mock Data
# Replace with backend data later
# =========================================================

demo_history = [
    {
        "id": "demo-1",
        "title": "The Silent Kingdom",
        "author": "Demo Author",
        "genres": ["Fantasy", "Adventure", "Romance"],
        "score": 86,
        "status": "Great Match",
        "date": "Oct 10, 2026",
        "cover_url": "",
        "synopsis": (
            "A fantasy adventure about a hidden kingdom "
            "and the people who seek to protect it."
        ),
        "matches": [
            {
                "title": "Favorite Genres",
                "description": (
                    "Fantasy and Adventure align with "
                    "your preferred genres."
                ),
            },
            {
                "title": "Character Preferences",
                "description": (
                    "The story features clever and independent "
                    "characters that may appeal to you."
                ),
            },
            {
                "title": "Story Elements",
                "description": (
                    "The adventure-driven plot may fit "
                    "your preferred storytelling style."
                ),
            },
        ],
        "mismatches": [
            {
                "title": "Genre Preferences",
                "description": (
                    "Romance is present in the story. "
                    "Its compatibility depends on your preferences."
                ),
            },
        ],
        "review_summary": {
            "positive": [
                "Readers enjoy the world-building.",
                "The characters are engaging.",
            ],
            "negative": [
                "Some readers find the pacing slow.",
            ],
            "mixed": [
                "Readers have different opinions about the ending.",
            ],
        },
        "sources": [
            {
                "title": "Book Information",
                "url": "https://books.google.com/",
            },
        ],
        "limitations": [
            "This is demonstration data, not verified reader feedback.",
            "The score is a mock value for UI testing.",
        ],
    },
    {
        "id": "demo-2",
        "title": "The Midnight Library",
        "author": "Demo Author",
        "genres": ["Mystery", "Drama"],
        "score": 72,
        "status": "Good Match",
        "date": "Oct 8, 2026",
        "cover_url": "",
        "synopsis": (
            "A mysterious story about choices, secrets, "
            "and unexpected discoveries."
        ),
        "matches": [
            {
                "title": "Mystery Elements",
                "description": "The story includes secrets and discoveries.",
            },
        ],
        "mismatches": [
            {
                "title": "Story Preferences",
                "description": "The pacing has not been verified.",
            },
        ],
        "review_summary": {
            "positive": ["Mock review: readers enjoy the central concept."],
            "negative": ["Mock review: some readers want more action."],
            "mixed": ["Mock review: opinions on the ending vary."],
        },
        "sources": [],
        "limitations": ["All analysis and review summaries are mock data."],
    },
    {
        "id": "demo-3",
        "title": "Beyond the Stars",
        "author": "Demo Author",
        "genres": ["Science Fiction", "Adventure"],
        "score": 58,
        "status": "Moderate Match",
        "date": "Oct 5, 2026",
        "cover_url": "",
        "synopsis": (
            "An adventure through distant worlds "
            "and unfamiliar civilizations."
        ),
        "matches": [
            {
                "title": "Adventure",
                "description": "The story includes an adventure-driven premise.",
            },
        ],
        "mismatches": [
            {
                "title": "Genre Alignment",
                "description": "The genre fit needs to be evaluated against user preferences.",
            },
        ],
        "review_summary": {
            "positive": ["Mock review: readers enjoy the imaginative setting."],
            "negative": ["Mock review: some readers find the story complex."],
            "mixed": ["Mock review: opinions on the characters differ."],
        },
        "sources": [],
        "limitations": ["All analysis and review summaries are mock data."],
    },
]

# Temporary front-end data.
# Backend can replace this data source later.
if "match_history" not in st.session_state:
    st.session_state.match_history = demo_history.copy()

history = st.session_state.match_history


# =========================================================
# Page Header
# =========================================================

with st.container(key="history-content"):

    st.markdown(
        """
        <h1>Reading<br>History</h1>

        <div class="history-description">
            Revisit your previous novel matches and discover
            how well each story aligns with your preferences.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")



    # =====================================================
    # Search Books
    # =====================================================

    search_query = st.text_input(
        "Search books",
        placeholder="Search by book title...",
        key="history-search",
        label_visibility="collapsed"
    )



    # =====================================================
    # History Summary
    # =====================================================

    filtered_history = [
        item
        for item in history
        if search_query.strip().lower()
        in item.get("title", "").lower()
    ]

    total_count = len(history)

    st.markdown(
        f"""
        <div class="history-count">
            <span>{len(filtered_history)} results</span>
            <span>{total_count} analyses in total</span>
        </div>
        """,
        unsafe_allow_html=True
    )



    # =====================================================
    # History List
    # =====================================================

    if filtered_history:

        for index, item in enumerate(filtered_history):

            title = escape(item.get("title", "Untitled Novel"))
            author = escape(item.get("author", "Unknown Author"))
            date = escape(item.get("date", "Date unavailable"))
            status = escape(item.get("status", "Not rated"))

            score = item.get("score", 0)
            genres = item.get("genres", [])
            synopsis = item.get("synopsis", "")
            cover_url = item.get("cover_url", "")

            genres_html = "".join(
                f'<span class="history-genre">{escape(str(genre))}</span>'
                for genre in genres
            )

            with st.container(
                border=True,
                key=f"history-card-{item.get('id', index)}"
            ):

                cover_col, info_col, score_col = st.columns(
                    [1, 3, 1.2],
                    vertical_alignment="center"
                )

                with cover_col:

                    if cover_url:
                        st.image(
                            cover_url,
                            use_container_width=True
                        )
                    else:
                        st.markdown(
                            """
                            <div class="history-cover-placeholder">
                                <span>📚</span>
                                <span>Book Cover</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                with info_col:

                    st.markdown(
                        f"""
                        <div class="history-book-title">{title}</div>
                        <div class="history-book-author">
                            By {author}
                        </div>
                        <div class="history-book-date">
                            {date}
                        </div>
                        <div class="history-genres">
                            {genres_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with score_col:

                    st.markdown(
                        f"""
                        <div class="history-score">
                            <div class="history-score-number">
                                {score}<span>/100</span>
                            </div>
                            <div class="history-score-status">
                                {status}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


                with st.expander("View Details", expanded=False):

                    # =====================================================
                    # Novel Details
                    # =====================================================

                    st.markdown(
                        '<div class="result-section-title">Novel Details</div>',
                        unsafe_allow_html=True,
                    )

                    detail_cover_col, detail_info_col = st.columns(
                        [0.75, 1.5],
                        gap="large",
                        vertical_alignment="top",
                    )

                    with detail_cover_col:
                        if cover_url:
                            st.image(cover_url, use_container_width=True)
                        else:
                            st.markdown(
                                """
                                <div class="history-cover-placeholder">
                                    <span>📚</span>
                                    <span>Book Cover</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    with detail_info_col:
                        st.markdown(
                            f'<div class="result-book-title">{title}</div>'
                            f'<div class="result-book-author">By {author}</div>',
                            unsafe_allow_html=True,
                        )

                        st.markdown("**Genres**")
                        st.write(", ".join(genres) if genres else "No genres available.")

                        st.markdown("**Synopsis**")
                        st.write(synopsis or "No synopsis available.")

                    st.divider()

                    # =====================================================
                    # Match Score
                    # =====================================================

                    st.markdown(
                        '<div class="result-section-title">Match Score</div>',
                        unsafe_allow_html=True,
                    )

                    score_col, summary_col = st.columns(
                        [0.75, 1.5],
                        gap="large",
                        vertical_alignment="center",
                    )

                    with score_col:
                        safe_score = max(0, min(100, int(score)))

                        st.markdown(
                            f"""
                            <div class="match-score-wrapper">
                                <div class="match-score-circle"
                                    style="--score: {safe_score * 3.6}deg;">
                                    <div class="match-score-inner">
                                        <div class="match-score-number">{safe_score}</div>
                                        <div class="match-score-label">/ 100</div>
                                    </div>
                                </div>
                                <div class="match-score-text">YOUR MATCH</div>
                                <div class="match-status">{status}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with summary_col:
                        st.markdown("### Overall Match Summary")
                        st.write(
                            "This score represents the simulated compatibility "
                            "between the novel and the reader's preferences."
                        )
                        st.caption("Demo score — not a verified AI evaluation.")

                    st.divider()

                    # =====================================================
                    # Match Analysis
                    # =====================================================

                    st.markdown(
                        '<div class="result-section-title">Match Analysis</div>',
                        unsafe_allow_html=True,
                    )

                    match_col, mismatch_col = st.columns(2, gap="large")

                    with match_col:
                        st.markdown("### ✓ Matches")

                        matches = item.get("matches", [])

                        if matches:
                            for point in matches:
                                if isinstance(point, dict):
                                    point_title = point.get("title", "Match")
                                    description = point.get("description", "")
                                else:
                                    point_title = "Match"
                                    description = str(point)

                                st.markdown(
                                    f"""
                                    <div class="result-positive">
                                        <div class="result-point-title">
                                            {escape(str(point_title))}
                                        </div>
                                        <div class="result-point-description">
                                            {escape(str(description))}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.caption("No matching points available.")

                    with mismatch_col:
                        st.markdown("### ⚠ Mismatches")

                        mismatches = item.get("mismatches", [])

                        if mismatches:
                            for point in mismatches:
                                if isinstance(point, dict):
                                    point_title = point.get("title", "Mismatch")
                                    description = point.get("description", "")
                                else:
                                    point_title = "Mismatch"
                                    description = str(point)

                                st.markdown(
                                    f"""
                                    <div class="result-warning">
                                        <div class="result-point-title">
                                            {escape(str(point_title))}
                                        </div>
                                        <div class="result-point-description">
                                            {escape(str(description))}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.caption("No mismatches available.")

                    st.divider()

                    # =====================================================
                    # Review Summary — Plain Text
                    # =====================================================

                    st.markdown(
                        '<div class="result-section-title">Review Summary</div>',
                        unsafe_allow_html=True,
                    )

                    review_summary = item.get("review_summary", {})

                    review_col1, review_col2, review_col3 = st.columns(
                        3,
                        gap="medium",
                    )

                    with review_col1:
                        st.markdown("#### What Readers Like")

                        positive_reviews = review_summary.get("positive", [])

                        if positive_reviews:
                            for review in positive_reviews:
                                st.text(str(review))
                        else:
                            st.caption("No positive review summary available.")

                    with review_col2:
                        st.markdown("#### Criticisms")

                        negative_reviews = review_summary.get("negative", [])

                        if negative_reviews:
                            for review in negative_reviews:
                                st.text(str(review))
                        else:
                            st.caption("No criticism summary available.")

                    with review_col3:
                        st.markdown("#### Mixed Opinions")

                        mixed_reviews = review_summary.get("mixed", [])

                        if mixed_reviews:
                            for review in mixed_reviews:
                                st.text(str(review))
                        else:
                            st.caption("No mixed review summary available.")

                    st.info(
                        "Review data has not been connected yet. "
                        "No reader opinions are being presented as verified facts."
                    )
                    # =====================================================
                    # Sources and Limitations — Dropdown
                    # =====================================================

                    with st.expander(
                        "Sources and Limitations",
                        expanded=False,
                    ):

                        # -------------------------------------------------
                        # Data Sources
                        # -------------------------------------------------

                        st.markdown("### Data Sources")

                        st.markdown(
                            """
                            - **Book information:** Google Books API / Open Library API
                            - **Reader reviews:** To be connected
                            - **Preference matching:** NovelMatch evaluation model
                            """
                        )

                        # -------------------------------------------------
                        # Review Data Overview
                        # -------------------------------------------------

                        st.markdown("### Review Data Overview")

                        st.write(
                            "Review counts, review excerpts, and source links "
                            "will be displayed after the review retrieval pipeline "
                            "has been implemented."
                        )

                        # -------------------------------------------------
                        # Limitations
                        # -------------------------------------------------

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

                        # -------------------------------------------------
                        # Review Sources
                        # -------------------------------------------------

                        st.markdown("### Review Sources")

                        st.caption(
                            "Individual review links will be displayed here "
                            "when real review sources are available."
                        )


    else:

        st.markdown(
            """
            <div class="history-empty">
                <div class="history-empty-icon">📖</div>
                <div class="history-empty-title">
                    No reading history found
                </div>
                <div class="history-empty-description">
                    Try another search or start a new novel analysis.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    # =====================================================
    # Footer Actions
    # =====================================================

    st.write("")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "← Back to Home",
            type="secondary",
            use_container_width=True,
            key="history-back-home"
        ):
            st.switch_page("main.py")

    with col2:
        if st.button(
            "Find a New Novel",
            type="primary",
            use_container_width=True,
            key="history-new-analysis"
        ):
            st.switch_page("pages/preview.py")

