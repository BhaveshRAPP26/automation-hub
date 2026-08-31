import streamlit as st
from pathlib import Path


st.set_page_config(
    page_title="Automation Hub - User Guide",
    page_icon="📖",
    layout="wide"
)


# ============================================================
# LOAD README
# ============================================================

readme_path = (
    Path(__file__).resolve().parent.parent / "README.md"
)


if not readme_path.exists():

    st.error(
        "Unable to locate the Automation Hub README."
    )

    st.code(
        str(readme_path)
    )

    st.stop()


readme_content = readme_path.read_text(
    encoding="utf-8"
)


# ============================================================
# DISPLAY
# ============================================================

st.markdown(
    readme_content
)