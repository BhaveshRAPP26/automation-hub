from urllib.parse import urlparse
import io
import re
import zipfile
import pandas as pd
import streamlit as st
import requests


st.set_page_config(page_title="HTML ID Extractor", page_icon="🔎", layout="wide")

if "results" not in st.session_state:
    st.session_state.results = {}



def get_filename(url):
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_")
    path = parsed.path.strip("/")
    if not path:
        path = "home"
    else:
        path = re.sub(r'[<>:"/\\|?* ]', "_", path.replace("/", "_"))
    return f"{domain}_{path}_ids.txt"

def extract_ids(url):
    """
    Downloads the HTML and extracts IDs beginning with 'link_' using regex.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=6000
    )

    response.raise_for_status()

    html = response.text

    # Match IDs beginning with link_
    ids = re.findall(
        r'id\s*=\s*["\'](link_[^"\']+)["\']',
        html,
        flags=re.IGNORECASE
    )

    return sorted(set(ids))




def categorize_ids(ids):
    """
    Categorize IDs into Header, Footer and Body.
    """

    rows = []

    for id_value in ids:

        id_lower = id_value.lower()

        if "link_header" in id_lower or "link_nav" in id_lower:
            category = "Header"

        elif "link_footer" in id_lower:
            category = "Footer"

        elif "link_btn_submit" in id_lower:
            category = "Form"

        else:
            category = "Body"

        rows.append({
            "Category": category,
            "ID": id_value
        })

    df = pd.DataFrame(rows)

    # Sort by category then ID
    category_order = {
        "Header": 0,
        "Body": 1,
        "Form": 2,
        "Footer": 3
    }

    df["Sort"] = df["Category"].map(category_order)

    df = (
        df.sort_values(["Sort", "ID"])
          .drop(columns="Sort")
          .reset_index(drop=True)
    )

    return df










st.title("🔎 HTML ID Extractor")
st.write(
    """
Paste one or more URLs below (one URL per line).

The application will:

- Visit each URL
- Extract every HTML ID beginning with **link_**
- Allow preview
- Generate a separate downloadable text file for each URL
"""
)
#txt=st.text_area("Enter one URL per line",height=200)
txt = st.text_area(
    "URLs",
    height=220,
    placeholder="""https://example.com
https://example2.com
https://example3.com""",
)

if st.button("🚀 Scrape IDs",type="primary"):
    urls=[u.strip() for u in txt.splitlines() if u.strip()]
    st.session_state.results={}
    prog=st.progress(0)
    status=st.empty()
    total = len(urls)

    for i,u in enumerate(urls):
        #status.info(f"Scraping {u}")
        status.info(f"Scraping ({i + 1}/{total}) : {u}")
        try:
            st.session_state.results[u]={"success":True,"ids":extract_ids(u)}
        except Exception as e:
            st.session_state.results[u]={"success":False,"error":str(e)}
        prog.progress((i+1)/max(len(urls),1))
    status.success("Finished!")

if st.session_state.results:
    zipbuf=io.BytesIO()
    with zipfile.ZipFile(zipbuf,"w",zipfile.ZIP_DEFLATED) as z:
        for u,r in st.session_state.results.items():
            if r["success"]:
                z.writestr(get_filename(u),"\n".join(r["ids"]))
    zipbuf.seek(0)
    st.download_button("📦 Download All Text Files",zipbuf,"html_ids.zip","application/zip")
    st.header("Results")
    for u,r in st.session_state.results.items():
        with st.expander(u,expanded=True):
            if not r["success"]:
                st.error(r["error"]); continue
            text = "\n".join(r["ids"])

            st.write(f"**IDs Found:** {len(r['ids'])}")

            # -------------------------------
            # Display grouped table
            # -------------------------------

            df = categorize_ids(r["ids"])

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            # -------------------------------
            # Download button
            # -------------------------------

            st.download_button(
                "📥 Download",
                text,
                file_name=get_filename(u),
                mime="text/plain",
                key=f"d_{u}"
            )
