import re
import requests
import pandas as pd
import streamlit as st
from io import BytesIO

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


def extract_ot_snippet(html):
    """
    Extract OneTrust script.
    """

    pattern = re.compile(
        r'data-domain-script=.*?</script>',
        re.DOTALL
    )

    match = pattern.search(html)

    if match:
        return match.group(0)

    return None


def detect_modal(snippet):
    """
    Detect modal type.
    """

    if snippet is None:
        return "Unknown", ""

    if 'data-domain-script="b6ad5043-a6c1-4c5e-b62c-4e6f6e544168"' in snippet:
        return (
            "Traditional Modal",
            "b6ad5043-a6c1-4c5e-b62c-4e6f6e544168"
        )

    if 'data-domain-script="8e9f51d5-bb35-43e2-8c8b-3dcd786f6159"' in snippet:
        return (
            "New Modal",
            "8e9f51d5-bb35-43e2-8c8b-3dcd786f6159"
        )

    if 'data-domain-script="c30d7be0-4ac6-4ab0-9d9b-b5f2a2190a2d"' in snippet:
        return (
            "Corporate Modal",
            "c30d7be0-4ac6-4ab0-9d9b-b5f2a2190a2d"
        )

    return "Unknown", ""


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

    for index, url in enumerate(urls):

        status_text.info(
            f"Processing {index + 1} of {total}\n\n{url}"
        )

        modal = "Error"
        domain_script = ""
        status = "Success"
        error = ""

        try:

            response = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            response.raise_for_status()

            snippet = extract_ot_snippet(
                response.text
            )

            if snippet:

                modal, domain_script = detect_modal(
                    snippet
                )

            else:

                modal = "Unknown"
                status = "No snippet found"

        except requests.exceptions.Timeout:

            status = "Timeout"
            error = "Request timed out"

        except requests.exceptions.SSLError:

            status = "SSL Error"
            error = "SSL certificate error"

        except requests.exceptions.HTTPError as e:

            status = "HTTP Error"
            error = str(e)

        except requests.exceptions.ConnectionError:

            status = "Connection Error"
            error = "Unable to connect"

        except Exception as e:

            status = "Error"
            error = str(e)

        results.append({
            "URL": url,
            "Domain Script": domain_script,
            "Modal": modal,
            "Status": status,
            "Error": error
        })

        df = pd.DataFrame(results)

        table_placeholder.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        progress_bar.progress(
            (index + 1) / total
        )

    status_text.success("Analysis complete!")


    # ------------------------------------
    # SUMMARY
    # ------------------------------------

    st.divider()

    st.subheader("Summary")

    total_sites = len(df)

    traditional = (df["Modal"] == "Traditional Modal").sum()
    new = (df["Modal"] == "New Modal").sum()
    corporate = (df["Modal"] == "Corporate Modal").sum()
    unknown = (df["Modal"] == "Unknown").sum()

    errors = (
        df["Status"] != "Success"
    ).sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total", total_sites)
    c2.metric("Traditional", traditional)
    c3.metric("New", new)
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
