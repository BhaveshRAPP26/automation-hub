from gtm_qa_automation import request_extractor as gq
import streamlit as st
import asyncio

st.set_page_config(layout='wide')
st.title("Website GTM QA")

st.header("Part 1")

text = st.text_area("Paste URLs here", height=150)

if st.button("Launch QA"):
    temp = text.split("\n")
    temp_list = []
    for elem in temp:
        if elem != "":
            temp_list.append(elem)
    
    
    for elem in temp_list:
        asyncio.run(gq.main(elem))

