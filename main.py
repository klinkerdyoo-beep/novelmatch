import streamlit as st
from components.navbar import navbar
from components.footer import footer
import base64


st.set_page_config(
    page_title="Novel Match",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/footer.css",
    "style/global.css",
    "style/home.css",
    "style/navbar.css",
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
# Assets
# =========================================================

with open("assets/hero-bg.png", "rb") as f:
    hero_bg = base64.b64encode(f.read()).decode()

with open("assets/chevron-right.svg", "rb") as f:
    chevron_right = base64.b64encode(f.read()).decode()


# =========================================================
# Hero + How It Works
# =========================================================

st.html(
    f"""
    <div class="page-sections">

        <!-- ================= HERO ================= -->

        <section
            class="hero"
            style="
                background-image:
                    url('data:image/png;base64,{hero_bg}');
            "
        >

            <div class="hero-content">

                <div class="hero-main">

                    <div class="hero-eyebrow">
                        Let AI help you
                    </div>

                    <h1 class="hero-title">
                        <span>Novel..</span>
                        <span>..Match</span> 
                    </h1>

                    <div class="hero-description">
                        Not every highly-rated novel is right for everyone.
                        Tell us what you like, and let NovelMatch help you
                        discover whether a story is right for you.
                    </div>

                </div>


                <div class="hero-action">

                    <a
                        class="hero-button"
                        href="/preferences"
                        target="_self"
                    >
                        <span class="hero-button-content" >Let's Get Started!</span>
                        <span>→</span>
                    </a>

                </div>

            </div>

        </section>


        <!-- ================= HOW ================= -->

        <section class="how-section">

            <div class="how-header">

                <div class="how-description">
                    Discover your match in three simple steps.
                    Tell us about your preferences, share the novel
                    you're interested in, and chat with NovelMatch
                    to discover how well it matches your taste.
                </div>

                <h2 class="how-title">
                    How It Works?
                </h2>

            </div>


            <div class="steps">

                <div class="step-card-big step-one">

                    <div class="step-card">

                        <div class="step-content">

                            <div class="step-title-big">
                                Tell Us About You
                            </div>

                            <div class="step-description">
                                Share your reading preferences.
                            </div>

                        </div>

                        <div class="step-number">
                            01
                        </div>

                    </div>

                    <a
                        href="/preferences"
                        target="_self"
                        class="step-link"
                    >
                        <span>Start Now!</span>

                        <span class="step-link-arrow">
                            <img
                                src="data:image/svg+xml;base64,{chevron_right}"
                                alt=""
                            />
                        </span>
                    </a>

                </div>


                <div class="step-card-big step-two">

                    <div class="step-card">

                        <div class="step-content">

                            <div class="step-title">
                                Tell Us About the Novel
                            </div>

                            <div class="step-description">
                                Enter the title and author of
                                the novel you're interested in.
                            </div>

                        </div>

                        <div class="step-number">
                            02
                        </div>

                    </div>

                </div>


                <div class="step-card-big step-three">

                    <div class="step-card">

                        <div class="step-content">

                            <div class="step-title">
                                Chat & Discover
                            </div>

                            <div class="step-description">
                                Chat with NovelMatch to discover
                                how well the novel matches
                                your personal taste.
                            </div>

                        </div>

                        <div class="step-number">
                            03
                        </div>

                    </div>

                </div>

            </div>

        </section>

        

    </div>
    
    """
)

# =========================================================
# Footer
# =========================================================

footer()