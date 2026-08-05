"""
Configuration values for the QA framework.
"""

from pathlib import Path

#############################################
# Directories
#############################################

BASE_DIR = Path(__file__).parent

REPORT_DIR = BASE_DIR / "reports"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
LOG_DIR = BASE_DIR / "logs"

REPORT_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

#############################################
# Playwright
#############################################

HEADLESS = False

DEFAULT_TIMEOUT = 30000

PAGE_LOAD_TIMEOUT = 60000

WAIT_AFTER_CLICK = 1500

WAIT_AFTER_CONSENT = 2500

WAIT_AFTER_NAVIGATION = 3000

#############################################
# OneTrust
#############################################

ONETRUST_EVENT = "OneTrustGroupsUpdated"

ONETRUST_VARIABLE = "OnetrustActiveGroups"

#############################################
# GA4
#############################################

GA_ENDPOINTS = [

    "google-analytics.com/g/collect",

    "analytics.google.com/g/collect"

]

#############################################
# Selectors
#############################################

LINK_SELECTOR = "[id^='link_']"

#############################################
# Screenshot Settings
#############################################

FULL_PAGE_SCREENSHOT = True

#############################################
# Reporting
#############################################

EXPORT_EXCEL = True

EXPORT_HTML = True

SAVE_DATALAYER = True

SAVE_GA_REQUESTS = True

#############################################
# Browser
#############################################

BROWSER = "chromium"