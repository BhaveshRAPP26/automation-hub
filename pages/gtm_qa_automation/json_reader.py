import json

# Load the JSON file
with open("ga_requests.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract all post_data values
post_data_list = [entry.get("post_data") for entry in data if "post_data" in entry]

# Filter out None values if you only want non-empty ones
post_data_list = [p for p in post_data_list if p]

req = []

# Print them
for i, pd in enumerate(post_data_list, 1):
    #print(f"Request {i}: {pd}")
    #print(f"{pd}")
    req.append(pd)
  
print(req)

req_dict = {}
for elem in req:
    if "ep.click_id_hit" in elem:
        dk = elem.split("ep.click_id_hit=")[1].split("&")[0]
        req_dict[dk] = elem

list_keys = list(req_dict.keys())

for k in list_keys:
    print(req_dict[k])



# Optionally save to another file
with open("post_data_only.json", "w", encoding="utf-8") as f:
    json.dump(post_data_list, f, indent=2, ensure_ascii=False)

