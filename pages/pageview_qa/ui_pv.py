import pageview_extractor as gq
import streamlit as st
import asyncio
import time

st.set_page_config(layout='wide')
st.title("Website GTM QA")


file = open("input_urls.txt","r")
lines = file.readlines()
file.close()

urls = []
for elem in lines:
    urls.append(elem.strip("\n"))


for url in urls:
    st.text(url)


if st.button("Launch QA"):
    
    start_time = time.time()
    for elem in urls:
        asyncio.run(gq.main(elem))

    st.text("QA Completed! Check the console for captured GA requests.")
    st.text("--- %s seconds ---" % (time.time() - start_time))