import streamlit as st
import streamlit.components.v1 as components
import base64
from html import escape
import time
from components.navbar import navbar

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
            unsafe_allow_html=True,
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
    unsafe_allow_html=True,
)

# =========================================================
# Error Messages
# =========================================================

error_messages = {
    "ANALYSIS_FAILED": {
        "title": "Analysis Failed",
        "description": (
            "Something went wrong while analyzing this novel."
        ),
        "suggestion": (
            "Please try another novel to get your personalized analysis."
        ),
    },
    "TIMEOUT": {
        "title": "Analysis Taking Too Long",
        "description": (
            "The analysis took longer than expected to complete."
        ),
        "suggestion": (
            "Please try again or choose another novel."
        ),
    },
}

# =========================================================
# GIF URLs
# =========================================================

LOADING_GIF_URL = (
    "https://tenor.com/view/"
    "laptop-hacking-hacker-cat-gif-5423768830271062600"
)

ERROR_GIF_URL = (
    "https://tenor.com/view/sorry-gif-18453366"
)

# =========================================================
# Loading / Error Animation
# =========================================================

def render_animation(
    is_error=False,
    error_message=None,
    error_title=None,
    error_suggestion=None,
    limitations=None,
):
    if is_error:
        gif_post_id = "18453366"
        gif_aspect_ratio = "0.790625"

        title = error_title or "Sorry, We Couldn't Analyze This Novel"
        description = error_message or (
            "We couldn't complete the analysis for this novel."
        )
        suggestion = error_suggestion or (
            "Try another novel with more available information."
        )
    else:
        gif_post_id = "5423768830271062600"
        gif_aspect_ratio = "1"

        title = "AI is processing your results"
        description = (
            "Please wait while AI analyzes your reading preferences "
            "and finds your novel match."
        )
        suggestion = None

    gif_url = (
        "https://tenor.com/view/sorry-gif-18453366"
        if is_error
        else "https://tenor.com/view/laptop-hacking-hacker-cat-gif-5423768830271062600"
    )

    gif_label = "Sorry GIF" if is_error else "Laptop Hacking GIF"

    suggestion_html = (
        f'<p class="nm-suggestion">{suggestion}</p>'
        if suggestion
        else ""
    )

    # Display limitations only when analysis fails.
    limitations = limitations if isinstance(limitations, list) else []

    limitations_html = ""

    if is_error and limitations:
        limitation_items = "".join(
            f"<li>{escape(limitation.strip())}</li>"
            for limitation in limitations
            if isinstance(limitation, str) and limitation.strip()
        )

        if limitation_items:
            limitations_html = f"""
                <div class="nm-limitations">
                    <p class="nm-limitations-title">Limitations</p>
                    <ul>
                        {limitation_items}
                    </ul>
                </div>
            """

    dots_html = (
        ""
        if is_error
        else """
        <div class="nm-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        """
    )

    components.html(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">

            <style>
                * {{
                    box-sizing: border-box;
                }}

                body {{
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: transparent;
                }}

                .nm-loading {{
                    min-height: 480px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: 24px 16px;
                }}

                .nm-gif {{
                    width: 260px;
                    max-width: 100%;
                    margin-bottom: 16px;
                    overflow: hidden;
                    border-radius: 18px;
                }}

                .nm-title {{
                    margin: 12px 0;
                    color: #172957;
                    font-size: 28px;
                    font-weight: 600;
                    line-height: 1.4;
                }}

                .nm-description {{
                    max-width: 440px;
                    margin: 0 0 10px;
                    color: #7488A1;
                    font-size: 15px;
                    line-height: 1.8;
                    overflow-wrap: anywhere;
                }}

                .nm-suggestion {{
                    max-width: 440px;
                    margin: 0;
                    color: #32A3A8;
                    font-size: 14px;
                    font-weight: 600;
                    line-height: 1.8;
                }}

                .nm-limitations {{
                    width: 100%;
                    max-width: 550px;
                    max-height: none;
                    height: auto;
                    overflow: visible;
                    box-sizing: border-box;

                    margin: 20px auto 0;
                    padding: 16px 20px;

                    text-align: left;
                    border-radius: 16px;
                    background: rgba(255, 255, 255, 0.72);
                }}

                .nm-limitations-title {{
                    margin: 0 0 8px;
                    color: #172957;
                    font-size: 14px;
                    font-weight: 600;
                }}

                .nm-limitations ul {{
                    margin: 8px 0 0;
                    padding-left: 24px;
                }}

                .nm-limitations li {{
                    margin-bottom: 6px;
                    line-height: 1.5;
                }}

                .nm-limitations li:last-child {{
                    margin-bottom: 0;
                }}
                .nm-dots {{
                    display: flex;
                    gap: 8px;
                    margin-top: 16px;
                }}

                .nm-dots span {{
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #32A3A8;
                    animation: bounce 1.2s infinite ease-in-out;
                }}

                .nm-dots span:nth-child(2) {{
                    background: #5DBD99;
                    animation-delay: .2s;
                }}

                .nm-dots span:nth-child(3) {{
                    animation-delay: .4s;
                }}

                @keyframes bounce {{
                    0%, 60%, 100% {{
                        transform: translateY(0);
                        opacity: .4;
                    }}

                    30% {{
                        transform: translateY(-5px);
                        opacity: 1;
                    }}
                }}

                @media (max-width: 600px) {{
                    .nm-title {{
                        font-size: 23px;
                    }}

                    .nm-gif {{
                        width: 220px;
                    }}
                }}

                @media (prefers-reduced-motion: reduce) {{
                    .nm-dots span {{
                        animation: none;
                    }}
                }}
            </style>
        </head>

        <body>
            <div class="nm-loading">

                <div class="nm-gif">
                    <div
                        class="tenor-gif-embed"
                        data-postid="{gif_post_id}"
                        data-share-method="host"
                        data-aspect-ratio="{gif_aspect_ratio}"
                        data-width="100%">
                        <a href="{gif_url}">{gif_label}</a>
                    </div>
                </div>

                <h1 class="nm-title">{title}</h1>

                <p class="nm-description">{description}</p>

                {limitations_html}

                {suggestion_html}

                {dots_html}

            </div>

            <script async src="https://tenor.com/embed.js"></script>
        </body>
        </html>
        """,
        height=(
            min(900, max(600, 560 + len(limitations) * 35))
            if is_error and limitations
            else 520
        ),
        scrolling=False,
    )

# =========================================================
# Session State
# =========================================================

if "analysis_complete" not in st.session_state:
    st.session_state["analysis_complete"] = False

if "analysis_error" not in st.session_state:
    st.session_state["analysis_error"] = False

if "analysis_started" not in st.session_state:  
    st.session_state["analysis_started"] = False



# =========================================================
# Loading Page
# =========================================================

with st.container(key="loading-page"):

    # -----------------------------------------------------
    # TEST BUTTON
    # IMPORTANT:
    # Remove this button before production.
    # It is only for testing the error UI.
    # -----------------------------------------------------

    st.caption(
        "DEV ONLY — Remove the test button before production."
    )

    test_error_type = st.selectbox(
        "Select Error Type",
        ["ANALYSIS_FAILED", "TIMEOUT"],
        key="test-error-type",
    )

    if st.button("🧪 Test Error State", key="test-analysis-error"):
        st.session_state["analysis_error"] = True
        st.session_state["analysis_complete"] = False
        st.session_state["analysis_error_type"] = test_error_type

        if test_error_type == "ANALYSIS_FAILED":
            st.session_state["limitations"] = [
                "Limited user reviews were available for this novel.",
                "Some character details could not be verified.",
                "The analysis may not reflect every aspect of the story.",
            ]
        else:
            st.session_state.pop("limitations", None)

        st.rerun()

    # -----------------------------------------------------
    # Error State
    # -----------------------------------------------------

    if st.session_state["analysis_error"]:

        error_type = st.session_state.get(
            "analysis_error_type",
            "ANALYSIS_FAILED",
        )

        error_info = error_messages.get(
            error_type,
            error_messages["ANALYSIS_FAILED"],
        )

        # Get limitations from session state.
        limitations = st.session_state.get("limitations", [])

        render_animation(
            is_error=True,
            error_message=error_info["description"],
            error_title=error_info["title"],
            error_suggestion=error_info["suggestion"],
            limitations=limitations if error_type == "ANALYSIS_FAILED" else [],
        )

        if st.button(
            "Try Another Novel",
            type="primary",
            use_container_width=True,
            key="try-another-novel",
        ):
            st.session_state["analysis_error"] = False
            st.session_state["analysis_complete"] = False
            st.session_state["analysis_started"] = False

            for key in (
                "novel_data",
                "review_data",
                "analysis_result",
                "limitations",
                "analysis_error_type",
            ):
                st.session_state.pop(key, None)

            st.switch_page("pages/novel.py")

    # -----------------------------------------------------
    # Navigate to Chat
    # -----------------------------------------------------

    elif st.session_state["analysis_complete"]:
        st.switch_page("pages/chat.py")

    # -----------------------------------------------------
    # Normal Loading State
    # -----------------------------------------------------

    else:
        render_animation(is_error=False)