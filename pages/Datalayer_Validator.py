import re

import streamlit as st
from playwright.sync_api import sync_playwright
import json
from urllib.parse import urlparse

st.set_page_config(page_title="DataLayer Scraper", layout="wide")

st.title("🌐 Website DataLayer Scraper")
st.write("Extract `window.dataLayer` from any website using Playwright.")

url = st.text_input(
    "Enter Website URL",
    placeholder="https://example.com"
)



def get_filename(url):
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_")
    path = parsed.path.strip("/")
    if not path:
        path = "home"
    else:
        path = re.sub(r'[<>:"/\\|?* ]', "_", path.replace("/", "_"))
    return f"{domain}_{path}_datalayer.json"

def scrape_datalayer(target_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Load page
        page.goto(target_url, wait_until="networkidle", timeout=60000)

        # Give additional time for GTM / JS pushes
        page.wait_for_timeout(3000)

        # Extract dataLayer
        datalayer = page.evaluate("""
            () => {
                if (typeof window.dataLayer === 'undefined') {
                    return null;
                }
                return window.dataLayer;
            }
        """)

        browser.close()
        return datalayer


if st.button("Scrape DataLayer", type="primary"):
    if not url:
        st.error("Please enter a URL.")
    else:
        try:
            with st.spinner("Loading page and extracting dataLayer..."):
                dl = scrape_datalayer(url)

            if dl is None:
                st.warning("No `window.dataLayer` found on this page.")
            else:
                st.success(f"Found dataLayer with {len(dl)} item(s).")

                # Summary table
                summary = []
                for i, item in enumerate(dl):
                    event = item.get("event", "(no event)") if isinstance(item, dict) else "(non-object)"
                    summary.append({
                        "Index": i,
                        "Event": event,
                        "Keys": len(item.keys()) if isinstance(item, dict) else "-"
                    })

                st.subheader("Event Summary")
                st.dataframe(summary, use_container_width=True)

                st.subheader("Full DataLayer")
                for i, item in enumerate(dl):
                    label = item.get("event", f"Item {i}") if isinstance(item, dict) else f"Item {i}"
                    with st.expander(f"{i}: {label}"):
                        st.json(item)

                # Download JSON
                #parsed = urlparse(url)
                #filename = f"{parsed.netloc.replace('.', '_')}_datalayer.json"
                filename = get_filename(url)
                st.download_button(
                    label="📥 Download DataLayer JSON",
                    data=json.dumps(dl, indent=2),
                    file_name=filename,
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"Error: {e}")