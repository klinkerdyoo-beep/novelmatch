import streamlit as st
import base64
from html import escape

from components.navbar import navbar
from components.api_client import (
    NovelMatchAPIError,
    get_preferences,
    get_novel_info,
    get_analysis_novel,
    analyze_novel,
    get_analyze_novel,
)


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

# =========================================================
# Session & Auth
# =========================================================

token = st.session_state.get("access_token")
if not token:
    st.warning("Session expired or not logged in. Please log in again.")
    st.switch_page("pages/login.py")
    st.stop()


# =========================================================
# Get User & Novel Data
# =========================================================

novel_title = st.session_state.get("novel_title", "").strip()
novel_author = st.session_state.get("novel_author", "").strip()
novel_synopsis = st.session_state.get("novel_synopsis", "").strip()
novel_genres = st.session_state.get("novel_genres", [])
novel_cover_url = st.session_state.get("novel_cover_url", "")
novel_id = st.session_state.get("novel_id")

# If novel_id is present but novel title is missing, fetch from backend
if novel_id and not novel_title:
    try:
        novel_res = get_novel_info(str(novel_id), token=token)
        novel_data = novel_res.get("data", {})
        novel_title = novel_data.get("title")
        novel_author = novel_data.get("author")
        novel_synopsis = novel_data.get("synopsis", "")
        novel_genres = novel_data.get("genre", [])
        novel_cover_url = novel_data.get("book_cover", "")
    except NovelMatchAPIError:
        pass

favorite_genres = st.session_state.get("enjoyed_genres") or st.session_state.get("favorite_genres", [])
disliked_genres = st.session_state.get("disliked_genres", [])

enjoy_characters = st.session_state.get("enjoyed_character") or st.session_state.get("enjoy_characters", [])
liked_characters = st.session_state.get("liked_character") or st.session_state.get("liked_characters", "")
disliked_character_description = st.session_state.get("disliked_character") or st.session_state.get("disliked_character_description", "")

liked_stories = st.session_state.get("enjoyed_story") or st.session_state.get("liked_stories", [])
disliked_stories = st.session_state.get("disliked_story") or st.session_state.get("disliked_stories", [])


# =========================================================
# Fetch / Execute Analysis
# =========================================================

if not st.session_state.get("analysis_result"):
    # 1. If novel_id exists, try to get stored analysis from match_history
    if novel_id:
        try:
            analyst_res = get_analysis_novel(str(novel_id), token=token)
            records = analyst_res.get("data", [])
            gemini_rec = next((r for r in records if "[Gemini]" in r.get("matches_summary", "")), None)
            gpt_rec = next((r for r in records if "[GPT-OSS]" in r.get("matches_summary", "")), None)
            if not gemini_rec and records:
                gemini_rec = records[0]
            if not gpt_rec and len(records) > 1:
                gpt_rec = records[1]

            st.session_state["analysis_result"] = {
                "gemini": {
                    "match_score": gemini_rec.get("score") if gemini_rec else None,
                    "match_level": gemini_rec.get("matches_level") if gemini_rec else None,
                    "summary": (gemini_rec.get("review_overview") or gemini_rec.get("matches_summary", "").replace("[Gemini] ", "")) if gemini_rec else None,
                    "matches": gemini_rec.get("matches", []) if gemini_rec else [],
                    "mismatches": gemini_rec.get("mismatches", []) if gemini_rec else [],
                    "limitations": gemini_rec.get("limitations", []) if gemini_rec else [],
                    "sources": gemini_rec.get("data_sources", []) if gemini_rec else [],
                    "review_summary": gemini_rec.get("review_summary", {}) if gemini_rec else {},
                } if gemini_rec else {},
                "gpt_oss": {
                    "match_score": gpt_rec.get("score") if gpt_rec else None,
                    "match_level": gpt_rec.get("matches_level") if gpt_rec else None,
                    "summary": (gpt_rec.get("review_overview") or gpt_rec.get("matches_summary", "").replace("[GPT-OSS] ", "")) if gpt_rec else None,
                    "matches": gpt_rec.get("matches", []) if gpt_rec else [],
                    "mismatches": gpt_rec.get("mismatches", []) if gpt_rec else [],
                    "limitations": gpt_rec.get("limitations", []) if gpt_rec else [],
                    "sources": gpt_rec.get("data_sources", []) if gpt_rec else [],
                    "review_summary": gpt_rec.get("review_summary", {}) if gpt_rec else {},
                } if gpt_rec else {},
            }
        except NovelMatchAPIError:
            pass

    # 2. If still no analysis_result, run POST /analysis with title and author
    if not st.session_state.get("analysis_result") and novel_title and novel_author:
        with st.spinner("AI is analyzing your novel match..."):
            try:
                payload = {
                    "title": novel_title,
                    "author": novel_author,
                    "synopsis": novel_synopsis,
                    "genre": novel_genres,
                }
                resp = analyze_novel(payload, token=token)
                st.session_state["analysis_result"] = resp.get("results", {})
                st.session_state["novel_id"] = resp.get("novel_id")
            except NovelMatchAPIError as exc:
                st.error(f"Analysis failed: {exc}")
                st.session_state["analysis_result"] = {}


# =========================================================
# Parse Model Analysis Results
# =========================================================

analysis_result = st.session_state.get("analysis_result") or {}
chatgpt_data = analysis_result.get("gpt_oss") or {}
gemini_data = analysis_result.get("gemini") or {}

has_chatgpt = bool(chatgpt_data and (chatgpt_data.get("match_score") is not None or chatgpt_data.get("summary")))

# --- ChatGPT Data ---
chatgpt_score = chatgpt_data.get("match_score")
# DEMO FALLBACK:
# if chatgpt_score is None:
#     chatgpt_score = 85
#     chatgpt_is_demo = True
# else:
#     chatgpt_is_demo = False
chatgpt_is_demo = False
chatgpt_score = int(chatgpt_score or 0)

if chatgpt_score >= 80:
    chatgpt_status = chatgpt_data.get("match_level") or "Great Match"
    chatgpt_status_class = "status-high"
elif chatgpt_score >= 60:
    chatgpt_status = chatgpt_data.get("match_level") or "Good Match"
    chatgpt_status_class = "status-medium"
else:
    chatgpt_status = chatgpt_data.get("match_level") or "Low Match"
    chatgpt_status_class = "status-low"

# DEMO FALLBACK:
# chatgpt_summary = chatgpt_data.get("summary") or (
#     "This section explains how well the novel matches your preferred genres, "
#     "character traits, and storytelling styles."
# )
chatgpt_summary = chatgpt_data.get("summary") or ""
chatgpt_matches = chatgpt_data.get("matches", [])
chatgpt_mismatches = chatgpt_data.get("mismatches", [])
chatgpt_reviews = chatgpt_data.get("review_summary", {})
chatgpt_sources = chatgpt_data.get("sources", [])
chatgpt_limitations = chatgpt_data.get("limitations", [])

# --- Gemini Data ---
gemini_score = gemini_data.get("match_score", 0)
# DEMO FALLBACK:
# if gemini_score is None:
#     gemini_is_demo = True
# else:
#     gemini_is_demo = False
gemini_is_demo = False
gemini_score = int(gemini_score or 0)

if gemini_score >= 80:
    gemini_status = gemini_data.get("match_level") or "Great Match"
    gemini_status_class = "status-high"
elif gemini_score >= 60:
    gemini_status = gemini_data.get("match_level") or "Good Match"
    gemini_status_class = "status-medium"
else:
    gemini_status = gemini_data.get("match_level") or "Low Match"
    gemini_status_class = "status-low"

# DEMO FALLBACK:
# gemini_summary = gemini_data.get("summary") or (
#     "Gemini evaluates how well this novel aligns with your reading preferences based on verified evidence."
# )
gemini_summary = gemini_data.get("summary") or ""
gemini_matches = gemini_data.get("matches", [])
gemini_mismatches = gemini_data.get("mismatches", [])
gemini_reviews = gemini_data.get("review_summary", {})
gemini_sources = gemini_data.get("sources", [])
gemini_limitations = gemini_data.get("limitations", [])


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


def format_preference(value):
    """Format preference data safely whether it is stored as text or a list."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (list, tuple, set)):
        return ", ".join(
            str(item).strip()
            for item in value
            if str(item).strip()
        )

    return str(value).strip()


def show_match_point(point="", explanation="", positive=True):
    css_class = "result-positive" if positive else "result-warning"
    point_clean = str(point or "").strip()
    desc_clean = str(explanation or "").strip()

    title_html = f'<div class="result-point-title">{escape(point_clean)}</div>' if point_clean else ""
    desc_html = f'<div class="result-point-description">{escape(desc_clean)}</div>' if desc_clean else ""

    st.markdown(
        f"""
        <div class="{css_class}">
            {title_html}
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# Header
# =========================================================

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
    # =========================================================
    # Book Information
    # =========================================================

    with st.container(border=False, key="novel-details-card"):

        show_section_title("Novel Details")

        cover_col, info_col = st.columns(
            [0.75, 1.5],
            gap="large",
            vertical_alignment="top",
        )

        with cover_col:
            if novel_cover_url and str(novel_cover_url).strip().startswith(("http://", "https://")):
                try:
                    st.image(
                        novel_cover_url,
                        use_container_width=True,
                    )
                except Exception:
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

            # DEMO FALLBACK:
            # display_genres = novel_genres or ["Fantasy", "Adventure", "Romance"]
            display_genres = novel_genres or []

            # Display Genres
            if display_genres:
                tags_html = "".join(
                    f'<span class="result-genre-tag">'
                    f'{escape(str(genre))}</span>'
                    for genre in display_genres
                )
                st.markdown(tags_html, unsafe_allow_html=True)

            # Display Synopsis
            # DEMO FALLBACK:
            # display_synopsis = (
            #     novel_synopsis
            #     or "A fantasy adventure about a hidden kingdom and the people who seek to protect it."
            # )
            display_synopsis = novel_synopsis or ""

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

    # Side-by-side columns for model analyses (or single column if GPT-OSS timed out / unavailable)
    if has_chatgpt:
        chatgpt_col, gemini_col = st.columns([1, 1], gap="large", vertical_alignment="top")
    else:
        st.info("ℹ️ ไม่พบผลวิเคราะห์จาก GPT-OSS (504 Timeout) ระบบแสดงเฉพาะผลการวิเคราะห์จาก Gemini")
        chatgpt_col = None
        gemini_col = st.container()

    if chatgpt_col is not None:
        # =========================================================
        # ChatGPT Analysis Column
        # =========================================================
        with chatgpt_col:
            st.markdown('<div class="model-heading model-heading-chatgpt">ChatGPT Analysis</div>', unsafe_allow_html=True)

            # Match Score
            with st.container(border=False, key="score-card"):
                st.html(
                    f"""
                    <div class="match-score-wrapper">
                        <div
                            class="match-score-circle"
                            style="--score: {chatgpt_score * 3.6}deg;"
                        >
                            <div class="match-score-inner">
                                <div class="match-score-number">{chatgpt_score}</div>
                                <div class="match-score-label">/ 100</div>
                            </div>
                        </div>
                        <div class="match-score-text">YOUR MATCH</div>
                        <div class="match-status {chatgpt_status_class}">
                            {escape(chatgpt_status)}
                        </div>
                    </div>
                    """
                )

                if chatgpt_summary:
                    st.markdown("### Overall Match Summary")
                    st.markdown(
                        f'<div class="result-summary">{escape(chatgpt_summary)}</div>',
                        unsafe_allow_html=True
                    )
                # DEMO FALLBACK:
                # if chatgpt_is_demo:
                #     st.caption("Demo score — will update with live evaluation result.")

            # Match Analysis
            with st.container(border=False, key="match-analysis-card"):
                show_section_title("Match Analysis")
                st.markdown("Understand which aspects may fit your preferences and which ones may not.")

                match_col, mismatch_col = st.columns(2, gap="large")

                with match_col:
                    st.markdown("### ✓ Matches")
                    if chatgpt_matches:
                        for item in chatgpt_matches:
                            show_match_point(
                                point=item.get("point", ""),
                                explanation=item.get("explanation", ""),
                                positive=True,
                            )
                    # DEMO FALLBACK:
                    # else:
                    #     if favorite_genres:
                    #         show_match_point(
                    #             "Your Favorite Genres",
                    #             "Your preferred genres are: "
                    #             + ", ".join(favorite_genres)
                    #             + ". The book's actual genres need to be verified."
                    #         )
                    #     else:
                    #         show_match_point("Genre Preferences", "You have not selected any favorite genres yet.")
                    #
                    #     character_summary = " ".join(
                    #         part for part in [
                    #             format_preference(liked_characters),
                    #             format_preference(enjoy_characters),
                    #         ] if part
                    #     )
                    #     if character_summary:
                    #         show_match_point("Characters You Enjoy", character_summary)
                    #
                    #     if liked_stories:
                    #         show_match_point("Story Elements You Enjoy", ", ".join(liked_stories))

                with mismatch_col:
                    st.markdown("### ⚠ Mismatches")
                    if chatgpt_mismatches:
                        for item in chatgpt_mismatches:
                            show_match_point(
                                point=item.get("point", ""),
                                explanation=item.get("explanation", ""),
                                positive=False,
                            )
                    # DEMO FALLBACK:
                    # else:
                    #     if disliked_genres:
                    #         show_match_point(
                    #             "Genres You Prefer to Avoid",
                    #             "Check whether the novel includes: " + ", ".join(disliked_genres),
                    #             positive=False
                    #         )
                    #     else:
                    #         show_match_point("Genre Mismatches", "No disliked genres provided.", positive=False)
                    #
                    #     if disliked_character_description.strip():
                    #         show_match_point(
                    #             "Character Traits You Dislike",
                    #             disliked_character_description,
                    #             positive=False
                    #         )
                    #
                    #     if disliked_stories:
                    #         show_match_point(
                    #             "Story Elements You Prefer to Avoid",
                    #             ", ".join(disliked_stories),
                    #             positive=False
                    #         )

            # Review Summary
            with st.container(border=False, key="review-summary-card"):
                show_section_title("Review Summary")
                st.markdown("### What do readers say about this novel?")

                review_col1, review_col2, review_col3 = st.columns(3, gap="medium")

                pos_reviews = chatgpt_reviews.get("positive", []) if isinstance(chatgpt_reviews, dict) else []
                neg_reviews = chatgpt_reviews.get("negative", []) if isinstance(chatgpt_reviews, dict) else []
                mix_reviews = chatgpt_reviews.get("mixed", []) if isinstance(chatgpt_reviews, dict) else []

                with review_col1:
                    st.markdown("#### What Readers Like")
                    if pos_reviews:
                        for rev in pos_reviews:
                            st.markdown(f"• {escape(str(rev))}")
                    # DEMO FALLBACK:
                    # else:
                    #     st.caption("Highlights from positive reader reviews will appear here.")

                with review_col2:
                    st.markdown("#### Criticisms")
                    if neg_reviews:
                        for rev in neg_reviews:
                            st.markdown(f"• {escape(str(rev))}")
                    # DEMO FALLBACK:
                    # else:
                    #     st.caption("Common concerns from reader reviews will appear here.")

                with review_col3:
                    st.markdown("#### Mixed Opinions")
                    if mix_reviews:
                        for rev in mix_reviews:
                            st.markdown(f"• {escape(str(rev))}")
                    # DEMO FALLBACK:
                    # else:
                    #     st.caption("Different reader perspectives will appear here.")

            # Sources and Limitations
            with st.container(border=False, key="source-card"):
                with st.expander("View Sources and Limitations", expanded=False):
                    st.markdown("### Data Sources")
                    if chatgpt_sources:
                        for src in chatgpt_sources:
                            title = src.get("title", "Source")
                            url = src.get("url")
                            if url:
                                st.markdown(f"- [{escape(str(title))}]({url})")
                            else:
                                st.markdown(f"- {escape(str(title))}")
                    # DEMO FALLBACK:
                    # else:
                    #     st.markdown(
                    #         """
                    #         - **Book information:** Google Books API / Open Library API
                    #         - **Reader reviews:** Retrieved online sources
                    #         - **Preference matching:** NovelMatch evaluation model
                    #         """
                    #     )

                    st.markdown("### Limitations")
                    if chatgpt_limitations:
                        for lim in chatgpt_limitations:
                            st.markdown(f"- {escape(str(lim))}")
                    # DEMO FALLBACK:
                    # else:
                    #     st.markdown(
                    #         """
                    #         - Book metadata may be incomplete or differ between sources.
                    #         - Reviews may not represent every reader's experience.
                    #         - The compatibility score depends on the quality and availability of retrieved information.
                    #         """
                    #     )

    # =========================================================
    # Gemini Analysis Column
    # =========================================================
    with gemini_col:
        st.markdown('<div class="model-heading model-heading-gemini">Gemini Analysis</div>', unsafe_allow_html=True)

        # Match Score
        with st.container(border=False, key="gemini-score-card"):
            st.html(
                f"""
                <div class="match-score-wrapper">
                    <div class="match-score-circle" style="--score: {gemini_score * 3.6}deg;">
                        <div class="match-score-inner">
                            <div class="match-score-number">{gemini_score}</div>
                            <div class="match-score-label">/ 100</div>
                        </div>
                    </div>
                    <div class="match-score-text">YOUR MATCH</div>
                    <div class="match-status {gemini_status_class}">
                        {escape(gemini_status)}
                    </div>
                </div>
                """
            )

            if gemini_summary:
                st.markdown("### Overall Match Summary")
                st.markdown(
                    f'<div class="result-summary">{escape(gemini_summary)}</div>',
                    unsafe_allow_html=True
                )
            # DEMO FALLBACK:
            # if gemini_is_demo:
            #     st.caption("Demo score — will update with live evaluation result.")

        # Match Analysis
        with st.container(border=False, key="gemini-match-analysis-card"):
            show_section_title("Match Analysis")
            st.markdown("A preference-based preview of how this novel could align with your reading preferences.")

            match_col, mismatch_col = st.columns(2, gap="large")

            with match_col:
                st.markdown("### ✓ Matches")
                if gemini_matches:
                    for item in gemini_matches:
                        show_match_point(
                            point=item.get("point", ""),
                            explanation=item.get("explanation", ""),
                            positive=True,
                        )
                # DEMO FALLBACK:
                # else:
                #     if favorite_genres:
                #         listed_genres = format_preference(novel_genres or ["Fantasy", "Adventure", "Romance"])
                #         show_match_point(
                #             "Your Favorite Genres",
                #             f"You enjoy {format_preference(favorite_genres)}. The displayed novel genres are {listed_genres}."
                #         )
                #     else:
                #         show_match_point("Genre Preferences", "You have not selected any favorite genres yet.")
                #
                #     character_summary = " ".join(
                #         part for part in [
                #             format_preference(liked_characters),
                #             format_preference(enjoy_characters),
                #         ] if part
                #     )
                #     if character_summary:
                #         show_match_point("Characters You Enjoy", character_summary)
                #
                #     if liked_stories:
                #         show_match_point("Story Elements You Enjoy", f"You enjoy stories featuring {format_preference(liked_stories)}.")

            with mismatch_col:
                st.markdown("### ⚠ Mismatches")
                if gemini_mismatches:
                    for item in gemini_mismatches:
                        show_match_point(
                            point=item.get("point", ""),
                            explanation=item.get("explanation", ""),
                            positive=False,
                        )
                # DEMO FALLBACK:
                # else:
                #     if disliked_genres:
                #         show_match_point(
                #             "Genres You Prefer to Avoid",
                #             f"Check whether the novel includes {format_preference(disliked_genres)}.",
                #             positive=False
                #         )
                #     else:
                #         show_match_point("Genre Mismatches", "No disliked genres provided.", positive=False)
                #
                #     if disliked_character_description.strip():
                #         show_match_point(
                #             "Character Traits You Dislike",
                #             f"You prefer to avoid: {disliked_character_description}.",
                #             positive=False
                #         )
                #
                #     if disliked_stories:
                #         show_match_point(
                #             "Story Elements You Prefer to Avoid",
                #             f"You prefer to avoid stories featuring {format_preference(disliked_stories)}.",
                #             positive=False
                #         )

        # Review Summary
        with st.container(border=False, key="gemini-review-summary-card"):
            show_section_title("Review Summary")
            st.markdown("### What do readers say about this novel?")

            review_col1, review_col2, review_col3 = st.columns(3, gap="medium")

            g_pos_reviews = gemini_reviews.get("positive", []) if isinstance(gemini_reviews, dict) else []
            g_neg_reviews = gemini_reviews.get("negative", []) if isinstance(gemini_reviews, dict) else []
            g_mix_reviews = gemini_reviews.get("mixed", []) if isinstance(gemini_reviews, dict) else []

            with review_col1:
                st.markdown("#### What Readers Like")
                if g_pos_reviews:
                    for rev in g_pos_reviews:
                        st.markdown(f"• {escape(str(rev))}")
                # DEMO FALLBACK:
                # else:
                #     st.caption("Readers may enjoy the imaginative setting and sense of adventure.")

            with review_col2:
                st.markdown("#### Criticisms")
                if g_neg_reviews:
                    for rev in g_neg_reviews:
                        st.markdown(f"• {escape(str(rev))}")
                # DEMO FALLBACK:
                # else:
                #     st.caption("Some readers may want deeper character development.")

            with review_col3:
                st.markdown("#### Mixed Opinions")
                if g_mix_reviews:
                    for rev in g_mix_reviews:
                        st.markdown(f"• {escape(str(rev))}")
                # DEMO FALLBACK:
                # else:
                #     st.caption("Opinions may differ on aspects of the plot and pacing.")

        # Sources and Limitations
        with st.container(border=False, key="gemini-source-card"):
            with st.expander("View Sources and Limitations", expanded=False):
                st.markdown("### Data Sources")
                if gemini_sources:
                    for src in gemini_sources:
                        title = src.get("title", "Source")
                        url = src.get("url")
                        if url:
                            st.markdown(f"- [{escape(str(title))}]({url})")
                        else:
                            st.markdown(f"- {escape(str(title))}")
                # DEMO FALLBACK:
                # else:
                #     st.markdown(
                #         """
                #         - **Book information:** Google Books API / Open Library API
                #         - **Reader reviews:** Retrieved online sources
                #         - **AI analysis:** Gemini API model evaluation
                #         """
                #     )

                st.markdown("### Limitations")
                if gemini_limitations:
                    for lim in gemini_limitations:
                        st.markdown(f"- {escape(str(lim))}")
                # DEMO FALLBACK:
                # else:
                #     st.markdown(
                #         """
                #         - Book metadata may be incomplete or differ between sources.
                #         - Reviews may not represent every reader's experience.
                #         - Results depend on the quality of retrieved information.
                #         """
                #     )

    # Full-width navigation
    st.divider()
    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        if st.button(
            "← Back to Home",
            use_container_width=True,
            key="result_back_to_home",
        ):
            st.switch_page("main.py")
