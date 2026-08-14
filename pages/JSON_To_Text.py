import json
from urllib.parse import parse_qsl, urlencode

# Input and output file paths
INPUT_JSON_FILE = "ga_requests.json"
OUTPUT_TEXT_FILE = "concatenated_ga4_requests.txt"


def concatenate_url_and_post_data(url, post_data):
    """
    Concatenate GA4 request URL with post_data parameters if post_data is not null.
    """
    if not post_data:
        return url

    # Clean post_data if needed
    post_data = post_data.strip()

    # If URL already has query parameters
    separator = "&" if "?" in url else "?"

    return f"{url}{separator}{post_data}"


def extract_requests(data):
    """
    Recursively extract all objects containing 'url' and 'post_data'.
    """
    results = []

    if isinstance(data, dict):
        if "url" in data:
            url = data.get("url")
            post_data = data.get("post_data")

            if url:
                final_url = concatenate_url_and_post_data(url, post_data)
                results.append(final_url)

        for value in data.values():
            results.extend(extract_requests(value))

    elif isinstance(data, list):
        for item in data:
            results.extend(extract_requests(item))

    return results


def main(uploaded_file):
    # Read uploaded JSON file
    data = json.load(uploaded_file)

    # Extract and concatenate requests
    final_urls = extract_requests(data)

    # Prepare output text
    output_text = "\n".join(final_urls) + ("\n" if final_urls else "")

    return final_urls, output_text


if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(layout="wide")
    st.title("JSON to Text")

    uploaded_file = st.file_uploader(
        "Upload JSON file",
        type=["json"]
    )

    if uploaded_file is not None:
        if st.button("Convert"):
            try:
                final_urls, output_text = main(uploaded_file)

                st.success(
                    f"Done. {len(final_urls)} URLs extracted."
                )

                st.download_button(
                    label="Download Text File",
                    data=output_text,
                    file_name=OUTPUT_TEXT_FILE,
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Error processing JSON file: {e}")
