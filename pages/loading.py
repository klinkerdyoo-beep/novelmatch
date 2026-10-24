import streamlit as st
import base64
import time
from pathlib import Path
from components.navbar import navbar

from components.loading_ui import (
    render_loading_header,
    render_loading_steps,
)


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Finding Your Novel Match | NovelMatch",
    layout="wide",
)

# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/loading.css",
]

for css_file in css_files:
    with open(css_file, encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )


navbar()


# =========================================================
# Background
# =========================================================

with open("assets/login-you-bg.png", "rb") as f:
    hero_bg = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <style> 
        .stApp {{
            background-image:
                url("data:image/png;base64,{hero_bg}");

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
# =========================================================

MOCK_NOVEL_DATA = {
    "title": "The Midnight Library",
    "author": "Matt Haig",
    "synopsis": (
        "Between life and death there is a library, "
        "where each book offers a chance to experience "
        "a different version of life."
    ),
    "genres": ["Fantasy", "Fiction", "Drama"],
}

MOCK_REVIEW_DATA = {
    "average_rating": 4.2,
    "review_count": 1250,
    "summary": (
        "Readers appreciate the imaginative concept, "
        "emotional storytelling, and exploration of life choices."
    ),
}

MOCK_ANALYSIS_RESULT = {
    "match_score": 87,
    "match_level": "High Match",
    "matched_traits": [
        "Thought-provoking story",
        "Character-driven narrative",
        "Fantasy elements",
    ],
    "mismatch_points": [
        "Some sections have a slower pace",
    ],
    "reasoning": (
        "This novel may suit readers who enjoy imaginative "
        "stories, meaningful character development, and "
        "reflection on life choices."
    ),
}


# =========================================================
# Mock Loading Workflow
# =========================================================


def run_mock_workflow(status_area):
    steps = [
        (0, 5, "Reading your preferences..."),
        (1, 25, "Exploring the novel..."),
        (2, 55, "Comparing your reading preferences..."),
        (3, 85, "Preparing your personalized results..."),
        (3, 100, "Analysis completed!"),
    ]

    for step, progress, message in steps:
        status_area.empty()

        with status_area.container():
            render_loading_steps(
                current_step=step,
                progress=progress,
                message=message,
            )

        time.sleep(0.7)

    st.session_state["novel_data"] = MOCK_NOVEL_DATA
    st.session_state["review_data"] = MOCK_REVIEW_DATA
    st.session_state["analysis_result"] = MOCK_ANALYSIS_RESULT
    st.session_state["analysis_complete"] = True


    st.session_state["novel_data"] = MOCK_NOVEL_DATA
    st.session_state["review_data"] = MOCK_REVIEW_DATA
    st.session_state["analysis_result"] = MOCK_ANALYSIS_RESULT
    st.session_state["analysis_complete"] = True

# =========================================================
# Loading Page UI
# =========================================================

with st.container(key="loading-page"):
    render_loading_header()

    status_area = st.empty()

    if not st.session_state.get("mock_loading_done", False):
        run_mock_workflow(status_area)

        st.session_state["mock_loading_done"] = True
        st.rerun()

    else:
        st.success("Your novel match is ready!")

        if st.button(
            "View My Results →",
            type="primary",
            use_container_width=True,
            key="view-results-button",
        ):
            st.switch_page("pages/chat.py")