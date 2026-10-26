import base64
from html import escape
from pathlib import Path

import streamlit as st

from components.navbar import navbar
from components.api_client import get_user_history, NovelMatchAPIError


# =========================================================
# Page Config
# =========================================================
st.set_page_config(page_title="My Reading History", layout="wide")


# =========================================================
# CSS
# =========================================================
for css_file in (
    "style/global.css",
    "style/navbar.css",
    "style/chat.css",
    "style/history.css",
):
    path = Path(css_file)
    if path.exists():
        st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# =========================================================
# Navbar + Background
# =========================================================
navbar()

background_path = Path("assets/about-you-bg.png")
if background_path.exists():
    encoded_bg = base64.b64encode(background_path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <style>
            .stApp {{
                background-image: url("data:image/png;base64,{encoded_bg}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Auth & Load History from Backend
# =========================================================
token = st.session_state.get("access_token")
if not token:
    st.warning("Session expired or not logged in. Please log in again.")
    st.switch_page("pages/login.py")
    st.stop()

# DEMO FALLBACK (Commented out):
# demo_history = [ ... ]

history = []
try:
    resp = get_user_history(token)
    history = resp.get("data", [])
except NovelMatchAPIError as exc:
    st.error(f"Cannot load history from backend: {exc}")
    history = []


def safe_text(value, fallback=""):
    return escape(str(value if value is not None else fallback))


def as_list(value):
    return value if isinstance(value, list) else []


def render_point(point, css_class, default_title):
    if isinstance(point, dict):
        point_title = point.get("point") or point.get("title") or default_title
        description = point.get("explanation") or point.get("description") or ""
    else:
        point_title, description = default_title, str(point)
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="result-point-title">{safe_text(point_title)}</div>
            <div class="result-point-description">{safe_text(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_review_column(heading, reviews, empty_message):
    st.markdown(f"#### {heading}")
    if reviews:
        for review in reviews:
            st.text(str(review))
    else:
        st.caption(empty_message)


# =========================================================
# Page Header + Search
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
        unsafe_allow_html=True,
    )

    search_query = st.text_input(
        "Search books",
        placeholder="Search by book title or author...",
        key="history-search",
        label_visibility="collapsed",
    )

    query = search_query.strip().casefold()
    filtered_history = [
        item for item in history
        if query in str(item.get("title", "")).casefold()
        or query in str(item.get("author", "")).casefold()
    ]

    count_col, sort_col = st.columns([2, 1], vertical_alignment="center")
    with count_col:
        st.markdown(
            f"""
            <div class="history-count">
                <span>{len(filtered_history)} results</span>
                <span>{len(history)} analyses in total</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sort_col:
        sort_choice = st.selectbox(
            "Sort history",
            ["Newest first", "Highest match", "Lowest match", "Title A–Z"],
            key="history-sort",
            label_visibility="collapsed",
        )

    if sort_choice == "Highest match":
        filtered_history.sort(
            key=lambda item: int(
                ((item.get("gemini") or item.get("chatgpt") or {}).get("score", item.get("score", 0))) or 0
            ),
            reverse=True,
        )
    elif sort_choice == "Lowest match":
        filtered_history.sort(
            key=lambda item: int(
                ((item.get("gemini") or item.get("chatgpt") or {}).get("score", item.get("score", 0))) or 0
            )
        )
    elif sort_choice == "Title A–Z":
        filtered_history.sort(key=lambda item: str(item.get("title", "")).casefold())
    else:
        filtered_history.sort(key=lambda item: history.index(item))

    if filtered_history:
        for index, item in enumerate(filtered_history):
            title = safe_text(item.get("title", "Untitled Novel"))
            author = safe_text(item.get("author", "Unknown Author"))
            
            # The history card uses the best available model score
            primary_model = item.get("gemini") or item.get("chatgpt") or {}
            if not isinstance(primary_model, dict):
                primary_model = {}
            raw_card_score = primary_model.get("score", item.get("score", 0))
            try:
                score = max(0, min(100, int(raw_card_score or 0)))
            except (TypeError, ValueError):
                score = 0
            status = safe_text(primary_model.get("status", item.get("status", "Not rated")))
            genres = as_list(item.get("genres"))
            synopsis = item.get("synopsis", "")
            cover_url = item.get("cover_url", "")
            genres_html = "".join(
                f'<span class="history-genre">{safe_text(genre)}</span>' for genre in genres
            )
            card_key = safe_text(item.get("id", index))

            with st.container(border=True, key=f"history-card-{card_key}"):
                cover_col, info_col, score_col = st.columns([0.85, 3.1, 1.15], vertical_alignment="center")

                with cover_col:
                    if cover_url and str(cover_url).strip().startswith(("http://", "https://")):
                        try:
                            st.image(cover_url, use_container_width=True)
                        except Exception:
                            st.markdown(
                                '<div class="history-cover-placeholder"><span>📚</span><span>Book Cover</span></div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(
                            '<div class="history-cover-placeholder"><span>📚</span><span>Book Cover</span></div>',
                            unsafe_allow_html=True,
                        )

                with info_col:
                    st.markdown(
                        f"""
                        <div class="history-book-title">{title}</div>
                        <div class="history-book-author">By {author}</div>
                        <div class="history-genres">{genres_html}</div>
                        """,
                        unsafe_allow_html=True,
                    )

                with score_col:
                    st.markdown(
                        f"""
                        <div class="history-score">
                            <div class="history-score-number">{score}<span>/100</span></div>
                            <div class="history-score-status">{status}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with st.expander("View Details", expanded=False):
                    # Shared novel information appears once above both model analyses.
                    st.markdown('<div class="result-section-title">Novel Details</div>', unsafe_allow_html=True)
                    detail_cover_col, detail_info_col = st.columns([0.75, 1.5], gap="large", vertical_alignment="top")
                    with detail_cover_col:
                        if cover_url and str(cover_url).strip().startswith(("http://", "https://")):
                            try:
                                st.image(cover_url, use_container_width=True)
                            except Exception:
                                st.markdown(
                                    '<div class="history-cover-placeholder"><span>📚</span><span>Book Cover</span></div>',
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.markdown(
                                '<div class="history-cover-placeholder"><span>📚</span><span>Book Cover</span></div>',
                                unsafe_allow_html=True,
                            )
                    with detail_info_col:
                        st.markdown(
                            f'<div class="result-book-title">{title}</div><div class="result-book-author">By {author}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("**Genres**")
                        st.write(", ".join(str(genre) for genre in genres) if genres else "No genres available.")
                        st.markdown("**Synopsis**")
                        st.write(synopsis or "No synopsis available.")

                    st.divider()

                    def get_model_data(model_key):
                        data = item.get(model_key, {})
                        return data if isinstance(data, dict) else {}

                    def model_score(model_data, fallback=None):
                        raw = model_data.get("score", fallback)
                        try:
                            return max(0, min(100, int(raw)))
                        except (TypeError, ValueError):
                            return None

                    def render_model_panel(model_key, model_label, accent_class, fallback_legacy=False):
                        model_data = get_model_data(model_key)
                        st.markdown(
                            f'<div class="model-heading {accent_class}">{model_label} Analysis</div>',
                            unsafe_allow_html=True,
                        )

                        # Prefer this model's own saved fields.
                        this_score = model_score(
                            model_data,
                            item.get("score") if fallback_legacy else None,
                        )
                        this_status = model_data.get("status") or (
                            item.get("status", "Not rated") if fallback_legacy else "No saved result"
                        )
                        this_summary = model_data.get("overall_summary") or (
                            item.get("overall_summary", "") if fallback_legacy else ""
                        )
                        this_matches = as_list(model_data.get("matches"))
                        this_mismatches = as_list(model_data.get("mismatches"))
                        this_reviews = model_data.get("review_summary", {})
                        if not isinstance(this_reviews, dict):
                            this_reviews = {}
                        this_demo = model_data.get("is_demo", item.get("is_demo", False))

                        if fallback_legacy:
                            if not this_matches:
                                this_matches = as_list(item.get("matches"))
                            if not this_mismatches:
                                this_mismatches = as_list(item.get("mismatches"))
                            if not this_reviews:
                                legacy_reviews = item.get("review_summary", {})
                                this_reviews = legacy_reviews if isinstance(legacy_reviews, dict) else {}

                        if not model_data or (this_score is None and not this_summary and not this_matches):
                            st.info(f"No saved {model_label} analysis is available for this history item.")
                            return

                        deg = (this_score * 3.6) if this_score is not None else 0
                        score_display = str(this_score) if this_score is not None else "--"
                        score_status_class = (
                            "status-high" if (this_score or 0) >= 80
                            else "status-medium" if (this_score or 0) >= 60
                            else "status-low"
                        )
                        score_col, summary_col = st.columns([0.85, 1.4], gap="medium", vertical_alignment="center")
                        with score_col:
                            st.markdown(
                                f'''<div class="match-score-wrapper">
                                    <div class="match-score-circle" style="--score: {deg}deg;">
                                        <div class="match-score-inner">
                                            <div class="match-score-number">{score_display}</div>
                                            <div class="match-score-label">/ 100</div>
                                        </div>
                                    </div>
                                    <div class="match-score-text">YOUR MATCH</div>
                                    <div class="match-status {score_status_class}">{safe_text(this_status)}</div>
                                </div>''',
                                unsafe_allow_html=True,
                            )
                        with summary_col:
                            st.markdown("### Overall Match Summary")
                            st.write(this_summary or "No saved overall summary is available for this model.")
                            if this_demo:
                                st.caption("Demo content — not a verified AI evaluation.")

                        st.markdown('<div class="result-section-title">Match Analysis</div>', unsafe_allow_html=True)
                        match_col, mismatch_col = st.columns(2, gap="medium")
                        with match_col:
                            st.markdown("### ✓ Matches")
                            if this_matches:
                                for point in this_matches:
                                    render_point(point, "result-positive", "Match")
                            else:
                                st.caption("No saved matching points available.")
                        with mismatch_col:
                            st.markdown("### ⚠ Mismatches")
                            if this_mismatches:
                                for point in this_mismatches:
                                    render_point(point, "result-warning", "Mismatch")
                            else:
                                st.caption("No saved mismatches available.")

                        st.markdown('<div class="result-section-title">Review Summary</div>', unsafe_allow_html=True)
                        review_col1, review_col2, review_col3 = st.columns(3, gap="small")
                        with review_col1:
                            render_review_column("What Readers Like", as_list(this_reviews.get("positive")), "No saved positive review summary.")
                        with review_col2:
                            render_review_column("Criticisms", as_list(this_reviews.get("negative")), "No saved criticism summary.")
                        with review_col3:
                            render_review_column("Mixed Opinions", as_list(this_reviews.get("mixed")), "No saved mixed review summary.")

                        with st.expander("View Sources and Limitations", expanded=False):
                            sources = as_list(model_data.get("sources", item.get("sources", []) if fallback_legacy else []))
                            limitations = as_list(model_data.get("limitations", item.get("limitations", []) if fallback_legacy else []))
                            st.markdown("### Data Sources")
                            if sources:
                                for source in sources:
                                    if isinstance(source, dict):
                                        source_title = safe_text(source.get("title", "Source"))
                                        source_url = str(source.get("url", "")).strip()
                                        if source_url.startswith(("https://", "http://")):
                                            st.markdown(f"- [{source_title}]({escape(source_url, quote=True)})")
                                        else:
                                            st.markdown(f"- {source_title}")
                                    else:
                                        st.markdown(f"- {safe_text(source)}")
                            else:
                                st.caption("No saved sources available.")
                            st.markdown("### Limitations")
                            if limitations:
                                for limitation in limitations:
                                    st.markdown(f"- {safe_text(limitation)}")
                            else:
                                st.markdown("- Book metadata and review coverage may be incomplete.")
                                st.markdown("- Scores should be treated as estimates, not definitive predictions.")

                    has_chatgpt = bool(item.get("chatgpt"))
                    has_gemini = bool(item.get("gemini"))

                    if has_chatgpt and has_gemini:
                        chatgpt_col, gemini_col = st.columns(2, gap="large", vertical_alignment="top")
                        with chatgpt_col:
                            with st.container(border=False, key=f"history-chatgpt-{card_key}"):
                                render_model_panel("chatgpt", "ChatGPT", "model-heading-chatgpt", fallback_legacy=True)
                        with gemini_col:
                            with st.container(border=False, key=f"history-gemini-{card_key}"):
                                render_model_panel("gemini", "Gemini", "model-heading-gemini", fallback_legacy=False)
                    elif has_gemini:
                        with st.container(border=False, key=f"history-gemini-{card_key}"):
                            render_model_panel("gemini", "Gemini", "model-heading-gemini", fallback_legacy=False)
                    elif has_chatgpt:
                        with st.container(border=False, key=f"history-chatgpt-{card_key}"):
                            render_model_panel("chatgpt", "ChatGPT", "model-heading-chatgpt", fallback_legacy=True)

    else:
        st.markdown(
            """
            <div class="history-empty">
                <div class="history-empty-icon">📖</div>
                <div class="history-empty-title">No reading history found</div>
                <div class="history-empty-description">Try another search or start a new novel analysis.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Home", type="secondary", use_container_width=True, key="history-back-home"):
            st.switch_page("main.py")
    with col2:
        if st.button("Find a New Novel", type="primary", use_container_width=True, key="history-new-analysis"):
            st.switch_page("pages/preview.py")
