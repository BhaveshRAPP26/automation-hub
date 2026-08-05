"""
browser.py

Playwright wrapper used by the QA framework.
"""

from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError
)

from config import (
    HEADLESS,
    DEFAULT_TIMEOUT,
    PAGE_LOAD_TIMEOUT,
    WAIT_AFTER_CLICK,
    WAIT_AFTER_NAVIGATION,
    FULL_PAGE_SCREENSHOT,
    SCREENSHOT_DIR,
    LINK_SELECTOR
)

from ga4 import GA4Collector


class BrowserManager:

    ############################################################

    def __init__(self):

        self.playwright = None

        self.browser = None

        self.context = None

        self.page = None

        self.ga4 = GA4Collector()

        self.original_domain = None

    ############################################################

    def start_step(self, step):

        self.ga4.start_step(step)

    ############################################################


    def step_requests(self):

        return self.ga4.current_requests()

    ############################################################


    def launch(self):

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=HEADLESS
        )

        self.context = self.browser.new_context()

        self.page = self.context.new_page()

        self.page.set_default_timeout(DEFAULT_TIMEOUT)

        self.page.on("request", self.ga4.capture)

    ############################################################

    def close(self):

        try:
            self.context.close()
        except:
            pass

        try:
            self.browser.close()
        except:
            pass

        try:
            self.playwright.stop()
        except:
            pass

    ############################################################

    def goto(self, url):

        self.original_domain = urlparse(url).netloc

        self.page.goto(
            url,
            timeout=PAGE_LOAD_TIMEOUT
        )

        self.page.wait_for_load_state("networkidle")

    ############################################################

    def current_url(self):

        return self.page.url

    ############################################################

    def wait(self, milliseconds):

        self.page.wait_for_timeout(milliseconds)

    ############################################################

    def screenshot(self, filename):

        path = Path(SCREENSHOT_DIR) / filename

        self.page.screenshot(
            path=str(path),
            full_page=FULL_PAGE_SCREENSHOT
        )

        return path

    ############################################################

    def clear_requests(self):

        self.ga4.start_step(step_number)

    ############################################################

    def latest_request(self):

        return self.ga4.latest()

    ############################################################

    def latest_event(self):

        return self.ga4.latest_event()

    ############################################################

    def request_count(self):

        return self.ga4.count()

    ############################################################

    def find_links(self):

        """
        Returns all visible elements whose id starts with link_
        """

        links = []

        locator = self.page.locator(LINK_SELECTOR)

        count = locator.count()

        for i in range(count):

            try:

                item = locator.nth(i)

                if item.is_visible():

                    links.append(item)

            except:

                pass

        return links

    ############################################################

    def click_link(self, index=0):

        links = self.find_links()

        if len(links) == 0:

            raise Exception("No link_ elements found.")

        if index >= len(links):

            raise Exception("Requested link index not found.")

        links[index].scroll_into_view_if_needed()

        links[index].click()

        self.wait(WAIT_AFTER_CLICK)

    ############################################################

    def disable_navigation(self):

        """
        Prevent every anchor navigation.
        """

        self.page.evaluate("""

        () => {

            document
                .querySelectorAll("a,[id^='link_']")
                .forEach(el=>{

                    el.addEventListener(
                        "click",

                        function(e){

                            e.preventDefault();

                        },

                        true
                    );

                });

        }

        """)

    ############################################################

    def enable_navigation(self):

        """
        Reload page to remove injected listeners.
        """

        self.page.reload()

        self.page.wait_for_load_state("networkidle")

    ############################################################

    def navigate_same_domain(self):

        """
        Click first same-domain anchor.
        """

        links = self.page.locator("a")

        count = links.count()

        current = urlparse(self.page.url).netloc

        for i in range(count):

            try:

                href = links.nth(i).get_attribute("href")

                if href is None:
                    continue

                if href.startswith("#"):
                    continue

                if href.startswith("mailto"):
                    continue

                if href.startswith("javascript"):
                    continue

                if href.startswith("/"):

                    links.nth(i).click()

                    self.page.wait_for_load_state("networkidle")

                    self.wait(WAIT_AFTER_NAVIGATION)

                    return True

                parsed = urlparse(href)

                if parsed.netloc == current:

                    links.nth(i).click()

                    self.page.wait_for_load_state("networkidle")

                    self.wait(WAIT_AFTER_NAVIGATION)

                    return True

            except:

                pass

        return False

    ############################################################

    def execute_js(self, script):

        return self.page.evaluate(script)

    ############################################################

    def title(self):

        return self.page.title()

    ############################################################

    def html(self):

        return self.page.content()

    ############################################################

    def console_log(self):

        logs = []

        def capture(msg):

            logs.append(msg.text)

        self.page.on("console", capture)

        return logs

    ############################################################

    def cookies(self):

        return self.context.cookies()

    ############################################################

    def reload(self):

        self.page.reload()

        self.page.wait_for_load_state("networkidle")