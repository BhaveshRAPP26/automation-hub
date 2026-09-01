import re
import pandas as pd
import streamlit as st
from io import BytesIO
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ------------------------------------
# PAGE CONFIG
# ------------------------------------

st.set_page_config(
    page_title="OneTrust Script Identifier",
    page_icon="✅",
    layout="wide"
)

st.title("OneTrust Script Identifier")
st.write(
    "Paste one URL per line, optionally supply a domain-script → label mapping, "
    "and click **Analyze**."
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


def extract_domain_script_guid(snippet):
    """
    Pull the raw data-domain-script value out of the script tag's HTML.
    Project-agnostic: this is just the identifier itself, with no
    assumption about what it maps to.
    """

    if not snippet:
        return None

    match = re.search(r'data-domain-script="([^"]+)"', snippet)

    return match.group(1) if match else None


def parse_mapping_text(text):
    """
    Parse a manually-pasted mapping of the form:
        <guid>,<label>
    or
        <guid>=<label>
    one entry per line. Returns a dict {guid: label}.
    """

    mapping = {}

    if not text:
        return mapping

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "," in line:
            guid, _, label = line.partition(",")
        elif "=" in line:
            guid, _, label = line.partition("=")
        else:
            continue

        guid = guid.strip().strip('"').strip("'")
        label = label.strip()

        if guid and label:
            mapping[guid] = label

    return mapping


def parse_mapping_file(uploaded_file):
    """
    Parse an uploaded CSV/XLSX mapping file into a dict {guid: label}.

    Column names are matched case-insensitively against a few common
    aliases so the tool doesn't force a rigid template. Falls back to
    treating the first two columns as (guid, label) if no recognizable
    headers are found.
    """

    mapping = {}

    if uploaded_file is None:
        return mapping

    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.warning(f"Could not read mapping file: {e}")
        return mapping

    if df.empty or df.shape[1] < 2:
        return mapping

    cols_lower = {c: str(c).strip().lower() for c in df.columns}

    guid_aliases = {"domain_script", "domain script", "script", "guid", "id", "domainscript"}
    label_aliases = {"label", "name", "modal", "group", "type", "modal type", "group label"}

    guid_col = next((c for c, lc in cols_lower.items() if lc in guid_aliases), None)
    label_col = next((c for c, lc in cols_lower.items() if lc in label_aliases), None)

    if guid_col is None or label_col is None:
        # Fall back to first two columns.
        guid_col, label_col = df.columns[0], df.columns[1]

    for _, row in df.iterrows():
        guid = str(row[guid_col]).strip().strip('"').strip("'")
        label = str(row[label_col]).strip()

        if guid and guid.lower() != "nan" and label and label.lower() != "nan":
            mapping[guid] = label

    return mapping


def analyze_url(page, url, mapping):
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
        guid = extract_domain_script_guid(snippet)

        if guid:
            label = mapping.get(guid, guid)

            return {
                "URL": url,
                "Domain Script": guid,
                "Group Label": label,
                "Mapped": guid in mapping,
                "Status": "Success",
                "Error": ""
            }

        return {
            "URL": url,
            "Domain Script": "",
            "Group Label": "No OneTrust Script Found",
            "Mapped": False,
            "Status": "No snippet found",
            "Error": ""
        }

    except PlaywrightTimeoutError:
        return {
            "URL": url,
            "Domain Script": "",
            "Group Label": "Error",
            "Mapped": False,
            "Status": "Timeout",
            "Error": "Page load or OneTrust script detection timed out"
        }

    except Exception as e:
        return {
            "URL": url,
            "Domain Script": "",
            "Group Label": "Error",
            "Mapped": False,
            "Status": "Error",
            "Error": str(e)
        }


# ------------------------------------
# SIDEBAR: OPTIONAL MAPPING
# ------------------------------------

with st.sidebar:
    st.header("Domain Script → Label Mapping")
    st.caption(
        "Optional. Without a mapping, the tool reports the raw domain-script "
        "GUID it finds on each page. Supply a mapping to translate GUIDs into "
        "readable labels (e.g. 'US Modal', 'EU Modal', 'Corporate')."
    )

    mapping_file = st.file_uploader(
        "Upload mapping file (CSV or XLSX)",
        type=["csv", "xlsx"],
        help="Two columns: a domain-script/GUID column and a label column. "
             "Header names are flexible (e.g. 'domain_script'/'guid'/'id' and 'label'/'name'/'modal')."
    )

    mapping_text = st.text_area(
        "Or paste mapping manually",
        height=150,
        placeholder="b6ad5043-a6c1-4c5e-b62c-4e6f6e544168, US Modal\n"
                    "8e9f51d5-bb35-43e2-8c8b-3dcd786f6159, CA Modal",
        help="One entry per line: guid,label  or  guid=label"
    )

    file_mapping = parse_mapping_file(mapping_file)
    text_mapping = parse_mapping_text(mapping_text)

    # Manual entries take priority over the uploaded file if both define the same guid.
    mapping = {**file_mapping, **text_mapping}

    if mapping:
        st.success(f"{len(mapping)} mapping entr{'y' if len(mapping) == 1 else 'ies'} loaded")
        with st.expander("View loaded mapping"):
            st.dataframe(
                pd.DataFrame(
                    [{"Domain Script": g, "Label": l} for g, l in mapping.items()]
                ),
                width='stretch',
                hide_index=True
            )
    else:
        st.info("No mapping loaded — raw GUIDs will be shown as the group label.")

    st.divider()

    template_buffer = BytesIO()
    pd.DataFrame(
        [{"domain_script": "<paste-guid-here>", "label": "<your-label-here>"}]
    ).to_csv(template_buffer, index=False)
    template_buffer.seek(0)

    st.download_button(
        "📄 Download mapping template (CSV)",
        data=template_buffer,
        file_name="domain_script_mapping_template.csv",
        mime="text/csv",
        width='stretch'
    )


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
    "Analyze OneTrust Scripts",
    type="primary",
    width='stretch'
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

            result = analyze_url(page, url, mapping)
            results.append(result)

            df = pd.DataFrame(results)

            table_placeholder.dataframe(
                df,
                width='stretch',
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
    successes = (df["Status"] == "Success").sum()
    errors = (df["Status"] != "Success").sum()
    distinct_scripts = df.loc[df["Domain Script"] != "", "Domain Script"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total_sites)
    c2.metric("Success", int(successes))
    c3.metric("Errors", int(errors))
    c4.metric("Distinct Domain Scripts", int(distinct_scripts))

    st.markdown("**Breakdown by Group Label**")

    group_counts = (
        df["Group Label"]
        .value_counts()
        .rename_axis("Group Label")
        .reset_index(name="Count")
    )

    st.dataframe(
        group_counts,
        width='stretch',
        hide_index=True
    )

    if mapping:
        unmapped_count = int((~df["Mapped"] & (df["Domain Script"] != "")).sum())
        if unmapped_count:
            st.warning(
                f"{unmapped_count} site(s) had a domain-script GUID with no matching entry "
                f"in your mapping — they're shown with the raw GUID as their label."
            )

    st.divider()

    st.subheader("Results")

    st.dataframe(
        df,
        width='stretch',
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
            sheet_name="Script Results",
            index=False
        )

        group_counts.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

    excel_buffer.seek(0)


    # ------------------------------------
    # DOWNLOAD BUTTON
    # ------------------------------------

    st.download_button(
        label="📥 Download Excel",
        data=excel_buffer,
        file_name="onetrust_script_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width='stretch'
    )
