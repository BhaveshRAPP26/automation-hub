"""
GA4 Network Request Parser
"""

from urllib.parse import urlparse
from urllib.parse import parse_qs

from config import GA_ENDPOINTS


class GA4Collector:

    def __init__(self):

        self.requests = []

    #########################################################

    def clear(self):

        self.requests = []

    #########################################################

    def capture(self, request):

        url = request.url

        if any(endpoint in url for endpoint in GA_ENDPOINTS):

            self.requests.append(url)

    #########################################################

    def latest(self):

        if len(self.requests) == 0:

            return None

        return self.requests[-1]

    #########################################################

    def count(self):

        return len(self.requests)

    #########################################################

    def all(self):

        return self.requests

    #########################################################

    def latest_parameters(self):

        latest = self.latest()

        if latest is None:

            return {}

        parsed = urlparse(latest)

        query = parse_qs(parsed.query)

        result = {}

        for key, value in query.items():

            if len(value) == 1:

                result[key] = value[0]

            else:

                result[key] = value

        return result

    #########################################################

    def latest_event(self):

        params = self.latest_parameters()

        return params.get("en", "")

    #########################################################

    def measurement_id(self):

        params = self.latest_parameters()

        return params.get("tid", "")

    #########################################################

    def client_id(self):

        params = self.latest_parameters()

        return params.get("cid", "")

    #########################################################

    def session_id(self):

        params = self.latest_parameters()

        return params.get("sid", "")