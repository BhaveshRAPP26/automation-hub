# capture_ga_requests.py
# Requires: pip install playwright
# Then: playwright install

import asyncio
import json
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright


# URL patterns to treat as GA4/measurement requests (common endpoints)
GA_PATTERNS = [
    "google-analytics.com/g/collect",
    "google-analytics.com/mp/collect",
    "google-analytics.com/r/collect",  # older-ish variants sometimes appear
    "/collect?v="                        # fallback for query-string collect calls
]


def is_ga_request(url: str) -> bool:


    lower = url.lower()
    return any(pat in lower for pat in GA_PATTERNS)


async def main(START_URL, ids_list):


    ga_requests = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)  # set True if you don't want UI
        context = await browser.new_context()
        page = await context.new_page()
        
       
        
        # Event handler to capture requests
        def handle_request(request):
            
            try:
                url = request.url
                if not is_ga_request(url):
                    return

                # gather headers
                headers = dict(request.headers)

                # post_data might be None for GETs or for beacons
                post_data = request.post_data

                # parse query parameters
                parsed = urlparse(url)
                query = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}

                entry = {
                    "url": url,
                    "method": request.method,
                    "headers": headers,
                    "query": query,
                    "post_data": post_data,
                }

                ga_requests.append(entry)

                # print a concise summary immediately
                print("=== Captured GA request ===")
                print("Method:", entry["method"])
                print("URL   :", entry["url"])
                print("Headers:", {k: headers[k] for k in headers})  # print all headers
                print("Query params:", entry["query"])
                print("Post data:", entry["post_data"])
                print("===========================\n")
            except Exception as e:
                print("Error handling request:", e)

        # Attach listener
        page.on("request", handle_request)

        
        # Navigate to your page
        await page.goto(START_URL, wait_until="networkidle")
        

        # Collect clickable elements: buttons, role=button, anchors, inputs
        #selector = "button, [role='button'], a[href], input[type='button'], input[type='submit']"
        #selector = "#link_header_logo, #cta_nav_1, #link_nav1_dd1"
        #selector = "#link_navdd1_2, #link_navdd1_3, #link_navdd1_4"
        
        #file = open("ids.txt","r")
        #lines = file.readlines()
        #file.close()


        selector_list = []
        for elem in ids_list:
            if "link_nav" not in elem and "link_video" not in elem and "link_exit" not in elem:
                selector_list.append("#"+elem.strip("\n"))


        print(selector_list)
        selector = ",".join(selector_list)

        elements = await page.query_selector_all(selector)
        print(f"Found {len(elements)} clickable elements matching selector: {selector}")
        
        """
#----------------------------
        dd = await page.query_selector_all("#link_nav_1")
        # Click each element — best effort (try/except). Pause a little after each click to allow network calls.
        for idx, el in enumerate(dd, start=1):
            try:
                # Scroll element into view first
                await el.hover()
                # Wait briefly for any GA calls triggered by the click
                await page.wait_for_timeout(5000)  # tweak if your site is slow
            except Exception as e:
                # Some elements may open new pages, be invisible, or require hover — skip them
                print(f"Skipping element #{idx} due to: {e}")
#----------------------------
        """
        ids_list = selector.strip(" ").split(",")

        
        

        await page.evaluate(f"""OneTrust.AllowAll()""")
        
        for ids in ids_list:
            try:
                await page.evaluate(f"""document.querySelector("{ids}").addEventListener("click", e => e.preventDefault());""")
            except Exception as e:
                print(f"Skipping element #{ids} due to: {e}")

        # Click each element — best effort (try/except). Pause a little after each click to allow network calls.
        for idx, el in enumerate(elements, start=1):
            try:
                # Scroll element into view first
                await el.scroll_into_view_if_needed()
                # Use mouse click via element to be closer to a user click 
                await el.click(timeout=5000)
                # Wait briefly for any GA calls triggered by the click
                await page.wait_for_timeout(5000)  # tweak if your site is slow
            except Exception as e:
                # Some elements may open new pages, be invisible, or require hover — skip them
                print(f"Skipping element #{idx} due to: {e}")


        # Wait a moment for any late requests to arrive
        await page.wait_for_timeout(5000)
        
        
        # Transform start_url into saveable format
        #FORMATTED_START_URL = f"{START_URL.replace('https://', '').replace('http://', '').replace('/', '_')}"
        FORMATTED_START_URL = START_URL.replace('https://', '').replace('http://', '').replace('/', '_')

        """
        # Save captured requests to disk
        #with open("ga_requests.json", "w", encoding="utf-8") as f: #overwriting
        with open("gtm_qa_automation/requests_json/" + FORMATTED_START_URL + ".json", "w", encoding="utf-8") as f: # appending
            json.dump(ga_requests, f, indent=2, ensure_ascii=False)

        print(f"\nDone. Captured {len(ga_requests)} GA requests")
        """


        # Prepare captured requests as a downloadable JSON file
        json_output = json.dumps(
            ga_requests,
            indent=2,
            ensure_ascii=False
        )

        print(f"\nDone. Captured {len(ga_requests)} GA requests")

        await browser.close()

        return {
            "filename": FORMATTED_START_URL + ".json",
            "content": json_output
        }




        

