"""
qa_runner.py

Executes OneTrust Consent Mode QA scenarios.
"""


from datetime import datetime

from browser import BrowserManager
from datalayer import DataLayerCollector
from onetrust import OneTrustHelper

from config import (
    WAIT_AFTER_CONSENT,
    WAIT_AFTER_CLICK,
    WAIT_AFTER_NAVIGATION
)

from utils import status



############################################################
# QA Runner
############################################################


class OneTrustQARunner:


    def __init__(
        self,
        url,
        screenshots=True
    ):

        self.url = url

        self.browser = BrowserManager()

        self.datalayer = DataLayerCollector()

        self.results = []

        self.screenshots = screenshots




    def begin_step(self, step):

        self.browser.start_step(step)

        self.capture_state()

    ########################################################
    # Add result
    ########################################################

    def add_result(
        self,
        step,
        action,
        expected,
        actual,
        passed,
        notes=""
    ):

        current_requests = self.browser.step_requests()

        ga_events = ", ".join(
            [r["event"] for r in current_requests]
        )

        self.results.append({

            "url_tested": self.url,

            "current_url": self.browser.current_url(),

            "step": step,

            "action": action,

            "expected": expected,

            "actual": actual,

            "active_groups":
                self.datalayer.latest_onetrust_groups(),

            "ga_event":
                ga_events,

            "ga_request_count":
                len(current_requests),

            "ga_requests":
                current_requests,

            "status":
                status(passed),

            "notes":
                notes,

            "timestamp":
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        })



    ########################################################
    # Capture datalayer
    ########################################################


    def capture_state(self):

        self.datalayer.refresh(
            self.browser.page
        )



    ########################################################
    # Screenshot
    ########################################################


    def screenshot(self,name):

        if self.screenshots:

            self.browser.screenshot(name)



    ########################################################
    # Run
    ########################################################


    def run(self):


        try:


            self.browser.launch()


            page = self.browser.page


            ################################################
            # STEP 1
            ################################################


            self.browser.goto(
                self.url
            )


            self.capture_state()


            groups = (
                self.datalayer
                .latest_onetrust_groups()
            )


            ga_event = (
                self.browser
                .latest_event()
            )


            self.add_result(

                1,

                "Page Load",

                "OneTrustGroupsUpdated + GA4 page_view",

                f"{groups} | {ga_event}",

                groups is not None

            )


            self.screenshot(
                "step1_initial_load.png"
            )



            ################################################
            # STEP 2
            ################################################


            self.browser.disable_navigation()


            self.begin_step(2)



            try:

                self.browser.click_link(
                    0
                )

                self.capture_state()


                self.add_result(

                    2,

                    "Click link_ element",

                    "No navigation. DataLayer updated",

                    f"{self.browser.current_url()} | "
                    f"Groups={self.datalayer.latest_onetrust_groups()} | "
                    f"GA4={self.browser.latest_event()}",

                    True

                )


            except Exception as e:


                self.add_result(

                    2,

                    "Click link_ element",

                    "Clickable element exists",

                    "",

                    False,

                    str(e)

                )



            self.screenshot(
                "step2_click.png"
            )



            ################################################
            # STEP 3
            ################################################


            self.begin_step(3)


            ot = OneTrustHelper(
                page
            )


            accepted = (
                ot.click_accept()
            )


            page.wait_for_timeout(
                WAIT_AFTER_CONSENT
            )


            no_request = (
                self.browser.request_count()
                ==
                0
            )


            self.capture_state()


            self.add_result(

                3,

                "Accept cookies",

                "No GA4 request after accept",

                f"Accepted={accepted}",

                no_request

            )


            self.screenshot(
                "step3_accept.png"
            )



            ################################################
            # STEP 4
            ################################################


            self.begin_step(4)


            try:


                self.browser.click_link(
                    1
                )


                self.capture_state()


                self.add_result(

                    4,

                    "Click second link_",

                    "GA4 request expected",

                    f"{self.browser.current_url()} | "
                    f"Groups={self.datalayer.latest_onetrust_groups()} | "
                    f"GA4={self.browser.latest_event()}",

                    self.browser.request_count() > 0

                )


            except Exception as e:


                self.add_result(

                    4,

                    "Click second link_",

                    "Element exists",

                    "",

                    False,

                    str(e)

                )



            ################################################
            # STEP 5
            ################################################


            self.browser.enable_navigation()


            self.begin_step(5)


            navigated = (
                self.browser
                .navigate_same_domain()
            )


            pageview = (
                self.browser.latest_event()
                ==
                "page_view"
            )


            self.capture_state()



            self.add_result(

                5,

                "Navigate to same-domain page",

                "GA4 page_view expected",

                f"{self.browser.current_url()} | {self.browser.latest_event()}",

                navigated and pageview

            )


            self.screenshot(
                "step5_navigation.png"
            )



            ################################################
            # STEP 6
            ################################################

            self.begin_step(6)

            rejected = (
                ot.reject_all_console()
            )


            page.wait_for_timeout(
                WAIT_AFTER_CONSENT
            )


            self.capture_state()


            groups = (
                self.datalayer
                .latest_onetrust_groups()
            )


            self.add_result(

                6,

                "Reject all cookies",

                "Consent groups updated",

                groups,

                rejected and groups is not None

            )



            ################################################
            # STEP 7
            ################################################


            self.browser.disable_navigation()


            self.begin_step(7)


            try:


                self.browser.click_link(
                    0
                )


                self.capture_state()


                no_request = (
                    self.browser.request_count()
                    ==
                    0
                )


                self.add_result(

                    7,

                    "Click after rejection",

                    "No GA4 request",

                    f"{self.browser.current_url()} | "
                    f"Groups={self.datalayer.latest_onetrust_groups()} | "
                    f"GA4={self.browser.latest_event()}",

                    no_request

                )


            except Exception as e:


                self.add_result(

                    7,

                    "Click after rejection",

                    "Clickable element",

                    "",

                    False,

                    str(e)

                )



            ################################################
            # STEP 8
            ################################################


            self.browser.enable_navigation()


            self.begin_step(8)


            self.browser.navigate_same_domain()


            no_pageview = (

                self.browser.latest_event()
                !=
                "page_view"

            )


            self.capture_state()



            self.add_result(

                8,

                "Navigate after Reject All",

               "No page_view",

                f"{self.browser.current_url()} | {self.browser.latest_event()}",

                no_pageview

            )



        except Exception as e:


            self.add_result(

                "ERROR",

                "Execution",

                "Complete execution",

                "",

                False,

                str(e)

            )


        finally:


            self.browser.close()



        return self.results