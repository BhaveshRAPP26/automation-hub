"""
datalayer.py

Helper functions for interacting with window.dataLayer
using Playwright.
"""

import json
from copy import deepcopy


class DataLayerCollector:

    def __init__(self):

        self.history = []

    ############################################################

    def snapshot(self, page):
        """
        Returns the entire window.dataLayer.
        """

        try:

            return page.evaluate("""
            () => {

                if(window.dataLayer){

                    return JSON.parse(JSON.stringify(window.dataLayer));

                }

                return [];

            }
            """)

        except Exception:

            return []

    ############################################################

    def refresh(self, page):
        """
        Saves the latest dataLayer snapshot.
        """

        dl = self.snapshot(page)

        self.history.append(deepcopy(dl))

        return dl

    ############################################################

    def latest(self):

        if len(self.history) == 0:

            return []

        return self.history[-1]

    ############################################################

    def latest_event(self, event_name):
        """
        Returns the latest occurrence of an event.
        """

        dl = self.latest()

        for item in reversed(dl):

            if isinstance(item, dict):

                if item.get("event") == event_name:

                    return item

        return None

    ############################################################

    def latest_variable(self, variable_name):
        """
        Returns latest occurrence of variable.
        """

        dl = self.latest()

        for item in reversed(dl):

            if isinstance(item, dict):

                if variable_name in item:

                    return item[variable_name]

        return None

    ############################################################

    def latest_onetrust_groups(self):

        dl = self.latest()

        for item in reversed(dl):

            if not isinstance(item, dict):

                continue

            if item.get("event") == "OneTrustGroupsUpdated":

                return item.get("OnetrustActiveGroups")

        return None

    ############################################################

    def latest_pageview(self):

        dl = self.latest()

        for item in reversed(dl):

            if not isinstance(item, dict):

                continue

            if item.get("event") == "page_view":

                return item

        return None

    ############################################################

    def latest_click(self):

        dl = self.latest()

        for item in reversed(dl):

            if not isinstance(item, dict):

                continue

            if item.get("event") == "click":

                return item

        return None

    ############################################################

    def event_count(self, event_name):

        dl = self.latest()

        count = 0

        for item in dl:

            if isinstance(item, dict):

                if item.get("event") == event_name:

                    count += 1

        return count

    ############################################################

    def contains_event(self, event_name):

        return self.event_count(event_name) > 0

    ############################################################

    def all_events(self):

        events = []

        dl = self.latest()

        for item in dl:

            if isinstance(item, dict):

                if "event" in item:

                    events.append(item["event"])

        return events

    ############################################################

    def dump_json(self):

        return json.dumps(self.latest(), indent=4)

    ############################################################

    def save(self, filepath):

        with open(filepath, "w", encoding="utf-8") as f:

            f.write(self.dump_json())