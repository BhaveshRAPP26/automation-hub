import urllib.parse
import streamlit as st

def req_breaker(requests):

    lines = requests.split("\n")

    for i in range(len(lines)):
        req = lines[i]

        val= urllib.parse.unquote(req)
        req1params = val.split("&")

        st.text("Request number " + str(i+1))
        for elem in req1params:
            if "dl" in elem or "en=" in elem  or "ep." in elem or "up." in elem:
            #if "ep.event_category" in elem or "tid=" in elem or "ep.event_action" in elem or "ep.event_label" in elem or "click_id" in elem:
                st.text(elem.replace("="," = ").replace("ep.","").replace("up.",""))
        st.text("\n")


st.set_page_config(layout='wide')
st.title("Program Title")

st.header("Part 1")

requests = st.text_area("Paste requests", height=150)

if st.button("Validate"):
    req_breaker(requests)
