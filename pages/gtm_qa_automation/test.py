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


def main():
    # Read JSON file
    with open(INPUT_JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract and concatenate requests
    final_urls = extract_requests(data)

    # Write to output text file
    with open(OUTPUT_TEXT_FILE, "w", encoding="utf-8") as f:
        for url in final_urls:
            f.write(url + "\n")

    print(f"Done. {len(final_urls)} URLs written to {OUTPUT_TEXT_FILE}")


if __name__ == "__main__":
    main()
