"""
ga4.py

GA4 Network Request Collector
"""

from datetime import datetime
from urllib.parse import urlparse, parse_qs


class GA4Collector:

    def __init__(self):

        # Every GA4 request captured during the session
        self.requests = []

        # Requests belonging to the current QA step
        self.current_step_requests = []

        self.current_step = None

    ###########################################################

    def start_step(self, step):

        """
        Called by the QA runner before each QA step.
        """

        self.current_step = step

        self.current_step_requests = []

    ###########################################################

    def end_step(self):

        """
        Returns requests generated during this step.
        """

        return self.current_step_requests.copy()

    ###########################################################

    def clear(self):

        self.current_step_requests = []

    ###########################################################

    def capture(self, request):

        """
        Automatically called by Playwright.
        """

        url = request.url

        if "google-analytics.com/g/collect" not in url \
        and "analytics.google.com/g/collect" not in url:

            return

        parsed = urlparse(url)

        params = parse_qs(parsed.query)

        flat = {}

        for key, value in params.items():

            if len(value) == 1:

                flat[key] = value[0]

            else:

                flat[key] = value

        record = {

            "timestamp":

                datetime.now().strftime(
                    "%H:%M:%S.%f"
                )[:-3],

            "step":

                self.current_step,

            "url":

                url,

            "event":

                flat.get(
                    "en",
                    ""
                ),

            "measurement_id":

                flat.get(
                    "tid",
                    ""
                ),

            "client_id":

                flat.get(
                    "cid",
                    ""
                ),

            "session_id":

                flat.get(
                    "sid",
                    ""
                ),

            "page_url":

                flat.get(
                    "dl",
                    ""
                ),

            "page_title":

                flat.get(
                    "dt",
                    ""
                ),

            "referrer":

                flat.get(
                    "dr",
                    ""
                ),

            "consent_gcs":

                flat.get(
                    "gcs",
                    ""
                ),

            "consent_gcd":

                flat.get(
                    "gcd",
                    ""
                ),

            "parameters":

                flat

        }

        self.requests.append(record)

        self.current_step_requests.append(record)

    ###########################################################

    def latest(self):

        if not self.requests:

            return None

        return self.requests[-1]

    ###########################################################

    def latest_event(self):

        latest = self.latest()

        if latest is None:

            return ""

        return latest["event"]

    ###########################################################

    def request_count(self):

        return len(self.current_step_requests)

    ###########################################################

    def all_requests(self):

        return self.requests

    ###########################################################

    def current_requests(self):

        return self.current_step_requests

    ###########################################################

    def latest_request_url(self):

        latest = self.latest()

        if latest is None:

            return ""

        return latest["url"]