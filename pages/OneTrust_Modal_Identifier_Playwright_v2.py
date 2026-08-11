import re
import pandas as pd
import streamlit as st
from io import BytesIO
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ------------------------------------
# PAGE CONFIG
# ------------------------------------

st.set_page_config(
    page_title="OneTrust Modal Validator",
    page_icon="✅",
    layout="wide"
)

st.title("OneTrust Modal Validator")
st.write(
    "Paste one URL per line and click **Analyze**."
)


# ------------------------------------
# HELPER FUNCTIONS
# ------------------------------------

def normalize_url(url):
    """
    Add https:// if missing.
    """

    url = url.strip()

    if not url:
        return None

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def extract_ot_snippet(page):
    """
    Extract the OneTrust script directly from the fully loaded page.

    Playwright loads and renders the page first, then the DOM is inspected.
    This is preferable to requests because OneTrust can be injected or
    modified by JavaScript after the initial HTML response.
    """

    # Look specifically for the OneTrust script element.
    scripts = page.locator('script[data-domain-script]')

    try:
        scripts.first.wait_for(state="attached", timeout=10000)
    except PlaywrightTimeoutError:
        return None

    count = scripts.count()

    if count == 0:
        return None

    # Return the complete script element HTML.
    return scripts.first.evaluate(
        "(element) => element.outerHTML"
    )


def detect_modal(snippet):
    """
    Detect modal type.
    """

    if snippet is None:
        return "Unknown", ""

    if 'data-domain-script="b6ad5043-a6c1-4c5e-b62c-4e6f6e544168"' in snippet:
        return (
            "US Modal",
            "b6ad5043-a6c1-4c5e-b62c-4e6f6e544168"
        )

    if 'data-domain-script="8e9f51d5-bb35-43e2-8c8b-3dcd786f6159"' in snippet:
        return (
            "CA Modal",
            "8e9f51d5-bb35-43e2-8c8b-3dcd786f6159"
        )

    if 'data-domain-script="c30d7be0-4ac6-4ab0-9d9b-b5f2a2190a2d"' in snippet:
        return (
            "Corporate Modal",
            "c30d7be0-4ac6-4ab0-9d9b-b5f2a2190a2d"
        )

    return "Unknown Modal", snippet.split("data-domain-script=")[1].split(">")[0].strip('"')


def analyze_url(page, url):
    """
    Load a URL using Playwright and inspect the rendered DOM
    after the page has finished loading.
    """

    try:
        page.goto(
            url,
            wait_until="load",
            timeout=30000
        )

        # Give scripts that run immediately after the load event a brief
        # opportunity to inject the OneTrust script into the DOM.
        page.wait_for_timeout(2000)

        snippet = extract_ot_snippet(page)

        if snippet:
            modal, domain_script = detect_modal(snippet)

            return {
                "URL": url,
                "Domain Script": domain_script,
                "Modal": modal,
                "Status": "Success",
                "Error": ""
            }

        return {
            "URL": url,
            "Domain Script": "",
            "Modal": "Unknown",
            "Status": "No snippet found",
            "Error": ""
        }

    except PlaywrightTimeoutError:
        return {
            "URL": url,
            "Domain Script": "",
            "Modal": "Error",
            "Status": "Timeout",
            "Error": "Page load or OneTrust script detection timed out"
        }

    except Exception as e:
        return {
            "URL": url,
            "Domain Script": "",
            "Modal": "Error",
            "Status": "Error",
            "Error": str(e)
        }


# ------------------------------------
# USER INPUT
# ------------------------------------

url_text = st.text_area(
    "Enter URLs (one URL per line)",
    height=250,
    placeholder="""https://example1.com
https://example2.com
https://example3.com"""
)

analyze = st.button(
    "Analyze OneTrust Modals",
    type="primary",
    use_container_width=True
)


# ------------------------------------
# ANALYSIS
# ------------------------------------

if analyze:

    # Clean input
    urls = [
        normalize_url(url)
        for url in url_text.splitlines()
        if normalize_url(url)
    ]

    if len(urls) == 0:
        st.warning("Please enter at least one URL.")
        st.stop()

    progress_bar = st.progress(0)
    status_text = st.empty()
    table_placeholder = st.empty()

    results = []
    total = len(urls)

    # Launch one browser and reuse it for all URLs.
    # This is considerably faster than starting a new browser for every URL.
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True
        )

        page = context.new_page()

        for index, url in enumerate(urls):

            status_text.info(
                f"Processing {index + 1} of {total}\n\n{url}"
            )

            result = analyze_url(page, url)
            results.append(result)

            df = pd.DataFrame(results)

            table_placeholder.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            progress_bar.progress(
                (index + 1) / total
            )

        browser.close()

    status_text.success("Analysis complete!")


    # ------------------------------------
    # SUMMARY
    # ------------------------------------

    st.divider()

    st.subheader("Summary")

    total_sites = len(df)

    us_modal = (df["Modal"] == "US Modal").sum()
    ca_modal = (df["Modal"] == "CA Modal").sum()
    corporate = (df["Modal"] == "Corporate Modal").sum()
    unknown = (df["Modal"] == "Unknown").sum()

    errors = (
        df["Status"] != "Success"
    ).sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total", total_sites)
    c2.metric("US", us_modal)
    c3.metric("CA", ca_modal)
    c4.metric("Corporate", corporate)
    c5.metric("Unknown", unknown)
    c6.metric("Errors", errors)

    st.divider()

    st.subheader("Results")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    # ------------------------------------
    # CREATE EXCEL
    # ------------------------------------

    excel_buffer = BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Modal Results",
            index=False
        )

    excel_buffer.seek(0)


    # ------------------------------------
    # DOWNLOAD BUTTON
    # ------------------------------------

    st.download_button(
        label="📥 Download Excel",
        data=excel_buffer,
        file_name="modal_validation_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
