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


async def main(START_URL):


    ga_requests = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)  # set True if you don't want UI
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
                """
                # print a concise summary immediately
                print("=== Captured GA request ===")
                print("Method:", entry["method"])
                print("URL   :", entry["url"])
                print("Headers:", {k: headers[k] for k in headers})  # print all headers
                print("Query params:", entry["query"])
                print("Post data:", entry["post_data"])
                print("===========================\n")
                """
            except Exception as e:
                print("Error handling request:", e)

        # Attach listener
        page.on("request", handle_request)

        try:
            # Navigate to your page
            await page.goto(START_URL, wait_until="networkidle")
            

            # Collect clickable elements: buttons, role=button, anchors, inputs
            #selector = "button, [role='button'], a[href], input[type='button'], input[type='submit']"
            #selector = "#link_header_logo, #cta_nav_1, #link_nav1_dd1"
            #selector = "#link_navdd1_2, #link_navdd1_3, #link_navdd1_4"
            
    
            #await page.evaluate(f"""OneTrust.AllowAll()""")
            

            # Wait a moment for any late requests to arrive
            #await page.wait_for_timeout(5000)
        
            
            # Transform start_url into saveable format
            #FORMATTED_START_URL = f"{START_URL.replace('https://', '').replace('http://', '').replace('/', '_')}"
            FORMATTED_START_URL = START_URL.replace('https://', '').replace('http://', '').replace('/', '_')


            # Save captured requests to disk
            #with open("ga_requests.json", "w", encoding="utf-8") as f: #overwriting
            with open("requests_json/" + FORMATTED_START_URL + ".json", "w", encoding="utf-8") as f: # appending
                json.dump(ga_requests, f, indent=2, ensure_ascii=False)

            #print(f"\nDone. Captured {len(ga_requests)} GA requests")
            print(f"\nDone for {START_URL}")
        except Exception as e:
            print("Error for ", START_URL)
        await browser.close()

