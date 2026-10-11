
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

                with st.expander("View Details"):

                    st.markdown("**Synopsis**")
                    st.write(
                        synopsis or "No synopsis available."
                    )

                    st.markdown("**Genres**")
                    st.write(
                        ", ".join(genres) if genres
                        else "No genres available."
                    )

                    st.markdown("**Match Score**")
                    st.progress(
                        max(0, min(100, int(score))) / 100
                    )
                    st.write(f"{score}/100")

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

