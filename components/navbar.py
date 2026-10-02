import streamlit as st
import base64

with open("assets/logo.png", "rb") as f:
    logo = base64.b64encode(f.read()).decode()

css_files = [
    "style/global.css",
    "style/navbar.css",
]

for css_file in css_files:
    with open(css_file, encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )


def navbar():

    st.html(
        f"""
        <div class="navbar">

            <a
                href="/"
                target="_self"
                class="nav-logo-link"
            >
                <img
                    src="data:image/png;base64,{logo}"
                    class="nav-logo"
                    alt="Novel Match"
                />
            </a>


            <div class="nav-actions">

                <a
                    href="/preferences"
                    target="_self"
                    class="nav-button"
                >
                    Preferences
                </a>

                <a
                    href="/login"
                    target="_self"
                    class="nav-button nav-login-button"
                >
                    Log in
                </a>

            </div>

        </div>
        """
    )