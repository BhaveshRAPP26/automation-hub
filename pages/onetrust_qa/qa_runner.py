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


        self.results.append(

            {

            "url":
                self.url,


            "current_url":
                self.browser.current_url(),


            "step":
                step,


            "action":
                action,


            "expected":
                expected,


            "actual":
                actual,


            "active_groups":
                self.datalayer.latest_onetrust_groups(),


            "ga_event":
                self.browser.latest_event(),


            "ga_requests":
                self.browser.request_count(),


            "status":
                status(passed),


            "notes":
                notes,


            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            }

        )



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


            self.browser.clear_requests()


            try:

                self.browser.click_link(
                    0
                )

                self.capture_state()


                self.add_result(

                    2,

                    "Click link_ element",

                    "No navigation. DataLayer updated",

                    self.datalayer
                    .latest_onetrust_groups(),

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


            self.browser.clear_requests()


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


            self.browser.clear_requests()


            try:


                self.browser.click_link(
                    1
                )


                self.capture_state()


                self.add_result(

                    4,

                    "Click second link_",

                    "GA4 request expected",

                    self.browser.latest_event(),

                    self.browser.request_count()
                    >
                    0

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


            self.browser.clear_requests()


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

                "Same domain navigation",

                "GA4 page_view expected",

                self.browser.latest_event(),

                navigated and pageview

            )



            self.screenshot(
                "step5_navigation.png"
            )



            ################################################
            # STEP 6
            ################################################


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


            self.browser.clear_requests()


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

                    self.browser.latest_event(),

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


            self.browser.clear_requests()


            self.browser.navigate_same_domain()


            no_pageview = (

                self.browser.latest_event()
                !=
                "page_view"

            )


            self.capture_state()



            self.add_result(

                8,

                "Navigation after rejection",

                "No GA4 page_view",

                self.browser.latest_event(),

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