import os
import re
import pandas as pd
from urllib.parse import urlparse, parse_qs

# ===== CONFIG =====
INPUT_FOLDER = "requests_json"
OUTPUT_FILE = "ga4_pageview_parameters.xlsx"
TARGET_TID_1 = "G-5KYQ407380"
TARGET_TID_2 = "G-941JK4VXK3"
TARGET_EVENT = "page_view"
# ==================

all_rows = []
all_params = set()

for filename in os.listdir(INPUT_FOLDER):
    if not filename.endswith(".json"):
        continue

    file_path = os.path.join(INPUT_FOLDER, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    page_row = {}
    page_row["page_url"] = filename.replace(".json", "")

    for line in lines:
        if '"url"' in line and (f"tid={TARGET_TID_1}" in line or f"tid={TARGET_TID_2}" in line) and f"en={TARGET_EVENT}" in line:

            # Extract the URL using regex
            match = re.search(r'"url"\s*:\s*"([^"]+)"', line)
            if not match:
                continue

            full_url = match.group(1)

            # Parse query parameters
            parsed_url = urlparse(full_url)
            query_params = parse_qs(parsed_url.query)

            for key, value in query_params.items():
                # value is a list from parse_qs → take first item
                page_row[key] = value[0]
                all_params.add(key)

            break  # stop after first matching page_view request

    all_rows.append(page_row)

# Create DataFrame
columns = ["page_url"] + sorted(all_params)
df = pd.DataFrame(all_rows, columns=columns)

# Export to Excel
df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")

print(f"\n✅ Excel file created: {OUTPUT_FILE}")
