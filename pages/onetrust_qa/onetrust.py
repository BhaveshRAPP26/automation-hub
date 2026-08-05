"""
onetrust.py

Utilities for interacting with OneTrust.
"""

import re
from playwright.sync_api import TimeoutError


class OneTrustHelper:

    def __init__(self, page):

        self.page = page

    ############################################################

    def banner_exists(self):

        selectors = [

            "#onetrust-banner-sdk",

            "#onetrust-consent-sdk",

            ".onetrust-pc-dark-filter",

            "#onetrust-button-group"

        ]

        for selector in selectors:

            try:

                if self.page.locator(selector).count() > 0:

                    return True

            except:

                pass

        return False

    ############################################################

    def click_accept(self):

        """
        Attempts several ways of accepting cookies.
        """

        buttons = [

            "#onetrust-accept-btn-handler",

            "button#accept-recommended-btn-handler",

            "button:has-text('Accept')",

            "button:has-text('Accept All')",

            "button:has-text('Allow All')"

        ]

        for selector in buttons:

            try:

                btn = self.page.locator(selector)

                if btn.count() > 0:

                    btn.first.click(timeout=3000)

                    return True

            except:

                pass

        try:

            self.page.get_by_role(
                "button",
                name=re.compile("accept", re.I)
            ).click(timeout=3000)

            return True

        except:

            return False

    ############################################################

    def reject_all_console(self):

        """
        Executes:

        OneTrust.RejectAll()
        """

        try:

            self.page.evaluate("""

            () => {

                if(typeof OneTrust !== "undefined"){

                    OneTrust.RejectAll();

                }

            }

            """)

            return True

        except:

            return False

    ############################################################

    def active_groups(self):

        try:

            return self.page.evaluate("""

            () => {

                if(typeof OneTrust === "undefined")

                    return null;

                return OneTrust.GetDomainData().ConsentModel.Name;

            }

            """)

        except:

            return None