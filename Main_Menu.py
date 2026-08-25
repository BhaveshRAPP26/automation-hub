import streamlit as st
import subprocess

subprocess.run(["playwright", "install"], check=True)

st.set_page_config(
    page_title="Automation Hub",
    page_icon="👋",
)



file = open("README.md", "r")
readme = file.read()
file.close()


st.markdown(readme)

