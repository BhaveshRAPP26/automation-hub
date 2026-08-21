"""
OneTrust Consent Mode QA Tool
=============================

Automates the manual OneTrust + GTM consent QA process:

  1. Load page -> read OnetrustActiveGroups from dataLayer -> capture pageview GA4 hit
  2. Click a "link_*" element -> confirm no navigation/new tab -> re-read groups -> capture GA4 hit
  3. Accept cookies via the OneTrust banner -> confirm NO GA4 network request fires
  4. Click another "link_*" element -> read groups -> capture GA4 hit
  5. Navigate to a different same-domain page -> read groups on load -> capture GA4 pageview hit
  6. Reject all via console command OneTrust.RejectAll() -> read groups
  7. Click a "link_*" element -> confirm NO GA4 network request fires -> read groups
  8. Navigate to a different same-domain page -> confirm NO GA4 pageview request fires -> read groups

Run with:
    pip install -r requirements.txt
    playwright install chromium
    streamlit run onetrust_consent_qa_app.py
"""

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd
import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

# --------------------------------------------------------------------------------------
# Constants / defaults
# --------------------------------------------------------------------------------------

DEFAULT_GA4_PATTERN = r"(google-analytics\.com/g/collect|analytics\.google\.com/g/collect|/g/collect)"
DEFAULT_ACCEPT_SELECTOR = "#onetrust-accept-btn-handler"
DEFAULT_BANNER_SELECTOR = "#onetrust-banner-sdk"

GET_ACTIVE_GROUPS_JS = """
() => {
    const dl = window.dataLayer || [];
    const matches = dl.filter(e => e && e.event === 'OneTrustGroupsUpdated');
    if (matches.length > 0) {
        const last = matches[matches.length - 1];
        if (last.OnetrustActiveGroups !== undefined) return last.OnetrustActiveGroups;
    }
    if (typeof window.OnetrustActiveGroups !== 'undefined') return window.OnetrustActiveGroups;
    return null;
}
"""

WAIT_FOR_GROUPS_EVENT_JS = """
() => {
    const dl = window.dataLayer || [];
    return dl.some(e => e && e.event === 'OneTrustGroupsUpdated');
}
"""

GET_FULL_DATALAYER_JS = """
() => {
    try { return JSON.stringify(window.dataLayer || []); } catch (e) { return '[]'; }
}
"""

REJECT_ALL_JS = """
() => {
    if (window.OneTrust && typeof OneTrust.RejectAll === 'function') {
        OneTrust.RejectAll();
        return true;
    }
    return false;
}
"""


# --------------------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------------------

@dataclass
class QAConfig:
    start_url: str
    second_url: str
    third_url: str
    ga4_pattern: str
    accept_selector: str
    link_selector_2: str
    link_selector_4: str
    link_selector_7: str
    headless: bool
    slow_mo_ms: int
    action_wait_ms: int
    load_wait_ms: int
    capture_screenshots: bool
    expected_groups: dict = field(default_factory=dict)


@dataclass
class StepResult:
    step: int
    title: str
    status: str  # PASS / FAIL / WARN / INFO / ERROR
    groups: Optional[str] = None
    notes: list = field(default_factory=list)
    ga4_hits: list = field(default_factory=list)
    all_requests_count: int = 0
    screenshot: Optional[bytes] = None
    url: Optional[str] = None


# --------------------------------------------------------------------------------------
# Playwright helpers
# --------------------------------------------------------------------------------------

def get_active_groups(page):
    try:
        return page.evaluate(GET_ACTIVE_GROUPS_JS)
    except Exception as e:
        return f"ERROR: {e}"


def wait_for_active_groups(page, timeout_ms):
    try:
        page.wait_for_function(WAIT_FOR_GROUPS_EVENT_JS, timeout=timeout_ms)
    except PWTimeoutError:
        pass
    return get_active_groups(page)


def get_full_datalayer(page):
    try:
        raw = page.evaluate(GET_FULL_DATALAYER_JS)
        return json.loads(raw)
    except Exception:
        return []


def reject_all_via_console(page):
    try:
        return bool(page.evaluate(REJECT_ALL_JS))
    except Exception:
        return False


def accept_onetrust_banner(page, selector, banner_selector, timeout_ms):
    """Returns (ok: bool, message: str)."""
    try:
        banner = page.locator(banner_selector)
        try:
            banner.wait_for(state="visible", timeout=timeout_ms)
        except PWTimeoutError:
            # banner may already be dismissed / not present this session
            pass
        btn = page.locator(selector)
        btn.wait_for(state="visible", timeout=timeout_ms)
        btn.click(timeout=timeout_ms)
        return True, "Clicked accept button"
    except Exception as e:
        return False, f"Could not click accept button ({selector}): {e}"


def get_link_locator(page, index, override_selector):
    if override_selector:
        return page.locator(override_selector)
    return page.locator("[id^='link_']").nth(index)


def click_and_observe(page, context, locator, wait_ms):
    """Click an element and detect whether it caused navigation or opened a new tab."""
    new_pages = []

    def on_page(p):
        new_pages.append(p)

    context.on("page", on_page)
    url_before = page.url
    click_error = None
    try:
        locator.scroll_into_view_if_needed(timeout=5000)
        locator.click(timeout=10000)
    except Exception as e:
        click_error = str(e)
    finally:
        context.remove_listener("page", on_page)

    page.wait_for_timeout(wait_ms)
    navigated = page.url != url_before
    opened_new_page = len(new_pages) > 0

    for p in new_pages:
        try:
            p.close()
        except Exception:
            pass

    return {
        "click_error": click_error,
        "navigated": navigated,
        "opened_new_page": opened_new_page,
        "url_before": url_before,
        "url_after": page.url,
    }


def parse_ga4_hit(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    def g(key):
        v = qs.get(key)
        return v[0] if v else None

    return {
        "url": url,
        "event_name": g("en"),
        "measurement_id": g("tid"),
        "page_location": g("dl"),
        "consent_gcs": g("gcs"),
        "consent_gcd": g("gcd"),
        "client_id": g("cid"),
    }


def filter_requests(requests_log, start_index, pattern):
    subset = requests_log[start_index:]
    if pattern:
        rx = re.compile(pattern, re.IGNORECASE)
        subset = [r for r in subset if rx.search(r["url"])]
    return subset


def same_hostname(url_a, url_b):
    try:
        return urlparse(url_a).netloc == urlparse(url_b).netloc
    except Exception:
        return False


def maybe_screenshot(page, capture):
    if not capture:
        return None
    try:
        return page.screenshot(full_page=False)
    except Exception:
        return None


def check_expected(actual, expected):
    """Loose comparison: exact match or substring containment either direction."""
    if not expected:
        return None  # not checked
    if actual is None:
        return False
    actual_s = str(actual)
    return actual_s == expected or expected in actual_s or actual_s in expected


# --------------------------------------------------------------------------------------
# Main QA flow
# --------------------------------------------------------------------------------------

def run_qa(cfg: QAConfig, progress_cb=None):
    results = []
    requests_log = []

    def log(msg):
        if progress_cb:
            progress_cb(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=cfg.headless, slow_mo=cfg.slow_mo_ms or 0)
        context = browser.new_context()

        def on_request(req):
            requests_log.append({
                "time": time.time(),
                "url": req.url,
                "method": req.method,
                "resource_type": req.resource_type,
            })

        context.on("request", on_request)
        page = context.new_page()
        page.set_default_timeout(15000)

        # ---------------- Step 1: initial load ----------------
        log("Step 1: loading start URL...")
        res = StepResult(1, "Initial page load - scrape dataLayer + pageview GA4 hit", "INFO")
        try:
            checkpoint = len(requests_log)
            page.goto(cfg.start_url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PWTimeoutError:
                pass
            groups = wait_for_active_groups(page, cfg.load_wait_ms)
            page.wait_for_timeout(cfg.load_wait_ms)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.groups = groups
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            exp = check_expected(groups, cfg.expected_groups.get(1))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(1)}' did not match actual '{groups}'")
            elif groups is None:
                res.status = "WARN"
                res.notes.append("No OneTrustGroupsUpdated event / OnetrustActiveGroups value found in dataLayer")
            else:
                res.status = "PASS" if exp else "INFO"

            if not ga_hits:
                res.notes.append("No GA4 pageview request captured - verify tag firing / pattern regex")
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 2: click link_* #1 ----------------
        log("Step 2: clicking first link_* element...")
        res = StepResult(2, "Click link_* element #1 - confirm no navigation, scrape groups + GA4 hit", "INFO")
        try:
            checkpoint = len(requests_log)
            locator = get_link_locator(page, 0, cfg.link_selector_2)
            obs = click_and_observe(page, context, locator, cfg.action_wait_ms)
            groups = get_active_groups(page)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.groups = groups
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            if obs["click_error"]:
                res.status = "ERROR"
                res.notes.append(f"Click failed: {obs['click_error']}")
            elif obs["navigated"] or obs["opened_new_page"]:
                res.status = "FAIL"
                res.notes.append(
                    f"Navigation was NOT prevented (navigated={obs['navigated']}, "
                    f"new_tab={obs['opened_new_page']}, url_before={obs['url_before']}, url_after={obs['url_after']})"
                )
            else:
                res.status = "PASS"
                res.notes.append("Click did not navigate or open a new tab, as expected")

            exp = check_expected(groups, cfg.expected_groups.get(2))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(2)}' did not match actual '{groups}'")
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 3: accept via OneTrust banner ----------------
        log("Step 3: accepting cookies via OneTrust banner...")
        res = StepResult(3, "Accept cookies via OneTrust banner - confirm NO GA4 network request fires", "INFO")
        try:
            checkpoint = len(requests_log)
            ok, msg = accept_onetrust_banner(page, cfg.accept_selector, DEFAULT_BANNER_SELECTOR, 10000)
            page.wait_for_timeout(cfg.action_wait_ms)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)
            res.notes.append(msg)

            if not ok:
                res.status = "ERROR"
            elif ga_hits:
                res.status = "FAIL"
                res.notes.append(f"{len(ga_hits)} GA4 request(s) fired when none were expected")
            else:
                res.status = "PASS"
                res.notes.append(
                    f"No GA4 request fired (total non-GA4 requests observed: {res.all_requests_count})"
                )
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 4: click link_* #2 ----------------
        log("Step 4: clicking second link_* element...")
        res = StepResult(4, "Click link_* element #2 - scrape groups + GA4 hit", "INFO")
        try:
            checkpoint = len(requests_log)
            locator = get_link_locator(page, 1, cfg.link_selector_4)
            obs = click_and_observe(page, context, locator, cfg.action_wait_ms)
            groups = get_active_groups(page)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.groups = groups
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            if obs["click_error"]:
                res.status = "ERROR"
                res.notes.append(f"Click failed: {obs['click_error']}")
            else:
                res.status = "INFO"
                if not ga_hits:
                    res.notes.append("No GA4 request captured after this interaction")

            exp = check_expected(groups, cfg.expected_groups.get(4))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(4)}' did not match actual '{groups}'")
            elif exp:
                res.status = "PASS"
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 5: navigate to second URL ----------------
        log("Step 5: navigating to second same-domain page...")
        res = StepResult(5, "Navigate to different same-domain page - scrape groups + pageview GA4 hit", "INFO")
        try:
            checkpoint = len(requests_log)
            domain_ok = same_hostname(cfg.start_url, cfg.second_url)
            page.goto(cfg.second_url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PWTimeoutError:
                pass
            groups = wait_for_active_groups(page, cfg.load_wait_ms)
            page.wait_for_timeout(cfg.load_wait_ms)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.groups = groups
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            if not domain_ok:
                res.notes.append("WARNING: second_url hostname differs from start_url hostname")

            if not ga_hits:
                res.status = "FAIL"
                res.notes.append("No GA4 pageview request captured on this navigation")
            else:
                res.status = "PASS"

            exp = check_expected(groups, cfg.expected_groups.get(5))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(5)}' did not match actual '{groups}'")
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 6: reject all via console ----------------
        log("Step 6: rejecting all via OneTrust.RejectAll()...")
        res = StepResult(6, "Reject all via console command OneTrust.RejectAll() - scrape groups", "INFO")
        try:
            found = reject_all_via_console(page)
            page.wait_for_timeout(cfg.action_wait_ms)
            groups = get_active_groups(page)
            res.groups = groups
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            if not found:
                res.status = "ERROR"
                res.notes.append("window.OneTrust.RejectAll was not found/callable on the page")
            else:
                res.status = "PASS"
                res.notes.append("OneTrust.RejectAll() executed")

            exp = check_expected(groups, cfg.expected_groups.get(6))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(6)}' did not match actual '{groups}'")
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 7: click link_* #3, expect no GA4 request ----------------
        log("Step 7: clicking third link_* element (post-rejection)...")
        res = StepResult(7, "Click link_* element #3 - confirm NO GA4 network request fires - scrape groups", "INFO")
        try:
            checkpoint = len(requests_log)
            locator = get_link_locator(page, 2, cfg.link_selector_7)
            obs = click_and_observe(page, context, locator, cfg.action_wait_ms)
            groups = get_active_groups(page)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.groups = groups
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            if obs["click_error"]:
                res.status = "ERROR"
                res.notes.append(f"Click failed: {obs['click_error']}")
            elif ga_hits:
                res.status = "FAIL"
                res.notes.append(f"{len(ga_hits)} GA4 request(s) fired when none were expected post-rejection")
            else:
                res.status = "PASS"
                res.notes.append("No GA4 request fired after rejection, as expected")

            exp = check_expected(groups, cfg.expected_groups.get(7))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(7)}' did not match actual '{groups}'")
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        # ---------------- Step 8: navigate to third URL, expect no pageview ----------------
        log("Step 8: navigating to third same-domain page (post-rejection)...")
        res = StepResult(8, "Navigate to different same-domain page - confirm NO pageview GA4 request - scrape groups", "INFO")
        try:
            target = cfg.third_url or cfg.second_url
            checkpoint = len(requests_log)
            domain_ok = same_hostname(cfg.start_url, target)
            page.goto(target, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PWTimeoutError:
                pass
            page.wait_for_timeout(cfg.load_wait_ms)
            groups = get_active_groups(page)
            ga_hits = filter_requests(requests_log, checkpoint, cfg.ga4_pattern)
            res.groups = groups
            res.ga4_hits = [parse_ga4_hit(r["url"]) for r in ga_hits]
            res.all_requests_count = len(requests_log) - checkpoint
            res.url = page.url
            res.screenshot = maybe_screenshot(page, cfg.capture_screenshots)

            if not domain_ok:
                res.notes.append("WARNING: third_url hostname differs from start_url hostname")

            if ga_hits:
                res.status = "FAIL"
                res.notes.append(f"{len(ga_hits)} GA4 pageview request(s) fired when none were expected")
            else:
                res.status = "PASS"
                res.notes.append("No GA4 pageview request fired after rejection, as expected")

            exp = check_expected(groups, cfg.expected_groups.get(8))
            if exp is False:
                res.status = "FAIL"
                res.notes.append(f"Expected groups '{cfg.expected_groups.get(8)}' did not match actual '{groups}'")
        except Exception as e:
            res.status = "ERROR"
            res.notes.append(str(e))
        results.append(res)

        browser.close()

    return results


# --------------------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------------------

def status_badge(status):
    colors = {
        "PASS": "🟢 PASS",
        "FAIL": "🔴 FAIL",
        "WARN": "🟡 WARN",
        "ERROR": "🟠 ERROR",
        "INFO": "🔵 INFO",
    }
    return colors.get(status, status)


def render_step(res: StepResult):
    with st.expander(f"Step {res.step} — {res.title}  |  {status_badge(res.status)}", expanded=(res.status in ("FAIL", "ERROR"))):
        cols = st.columns([1, 1])
        with cols[0]:
            st.markdown("**OnetrustActiveGroups**")
            st.code(str(res.groups), language="text")
            if res.url:
                st.markdown(f"**URL:** `{res.url}`")
        with cols[1]:
            st.markdown(f"**GA4 requests matched:** {len(res.ga4_hits)}  |  **Total requests seen:** {res.all_requests_count}")
            if res.ga4_hits:
                df = pd.DataFrame(res.ga4_hits)
                st.dataframe(df, use_container_width=True, hide_index=True)

        if res.notes:
            for n in res.notes:
                st.markdown(f"- {n}")

        if res.screenshot:
            st.image(res.screenshot, caption=f"Step {res.step} screenshot")


def build_summary_df(results):
    rows = []
    for r in results:
        rows.append({
            "Step": r.step,
            "Description": r.title,
            "OnetrustActiveGroups": r.groups,
            "GA4 Hits": len(r.ga4_hits),
            "Status": r.status,
        })
    return pd.DataFrame(rows)


def results_to_json(results):
    payload = []
    for r in results:
        payload.append({
            "step": r.step,
            "title": r.title,
            "status": r.status,
            "groups": r.groups,
            "url": r.url,
            "notes": r.notes,
            "ga4_hits": r.ga4_hits,
            "all_requests_count": r.all_requests_count,
        })
    return json.dumps(payload, indent=2, default=str)


def main():
    st.set_page_config(page_title="OneTrust Consent QA", layout="wide")
    st.title("🍪 OneTrust Consent Mode QA")
    st.caption("Automates the 8-step manual QA process for OneTrust + GTM consent tracking.")

    if "qa_results" not in st.session_state:
        st.session_state.qa_results = None
    if "qa_ran_at" not in st.session_state:
        st.session_state.qa_ran_at = None

    with st.sidebar:
        st.header("Configuration")

        start_url = st.text_input("Start URL (Step 1)", placeholder="https://example.com/page-a")
        second_url = st.text_input("Second page URL, same domain (Step 5)", placeholder="https://example.com/page-b")
        third_url = st.text_input(
            "Third page URL, same domain (Step 8) — optional, defaults to second URL",
            placeholder="https://example.com/page-c",
        )

        st.divider()
        st.subheader("Element selectors")
        st.caption("Leave blank to auto-pick the 1st/2nd/3rd element matching `[id^='link_']`.")
        link_selector_2 = st.text_input("Link selector for Step 2 (override)", value="")
        link_selector_4 = st.text_input("Link selector for Step 4 (override)", value="")
        link_selector_7 = st.text_input("Link selector for Step 7 (override)", value="")
        accept_selector = st.text_input("OneTrust accept-all button selector", value=DEFAULT_ACCEPT_SELECTOR)

        st.divider()
        st.subheader("Network matching")
        ga4_pattern = st.text_input("GA4 request regex pattern", value=DEFAULT_GA4_PATTERN)
        st.caption("Pass/fail checks for 'no network request' steps are scoped to requests matching this pattern.")

        st.divider()
        st.subheader("Timing & browser")
        headless = st.checkbox("Headless mode", value=True, help="Turn off to visually watch the browser (requires a display).")
        slow_mo_ms = st.slider("Slow motion (ms per action)", 0, 1000, 0, step=50)
        action_wait_ms = st.slider("Wait after click actions (ms)", 500, 8000, 2000, step=250)
        load_wait_ms = st.slider("Wait after page loads (ms)", 500, 10000, 3000, step=250)
        capture_screenshots = st.checkbox("Capture screenshots per step", value=True)

        with st.expander("Expected OnetrustActiveGroups values (optional)"):
            st.caption("If provided, the tool checks the scraped value against these for an automatic PASS/FAIL.")
            exp1 = st.text_input("Expected value — Step 1", value="")
            exp2 = st.text_input("Expected value — Step 2", value="")
            exp4 = st.text_input("Expected value — Step 4", value="")
            exp5 = st.text_input("Expected value — Step 5", value="")
            exp6 = st.text_input("Expected value — Step 6 (rejected)", value="")
            exp7 = st.text_input("Expected value — Step 7 (rejected)", value="")
            exp8 = st.text_input("Expected value — Step 8 (rejected)", value="")

        run_clicked = st.button("▶ Run QA Suite", type="primary", use_container_width=True)
        clear_clicked = st.button("Clear results", use_container_width=True)

    if clear_clicked:
        st.session_state.qa_results = None
        st.session_state.qa_ran_at = None

    if run_clicked:
        if not start_url or not second_url:
            st.error("Please provide at least the Start URL and Second page URL.")
        else:
            expected_groups = {
                1: exp1 or None, 2: exp2 or None, 4: exp4 or None,
                5: exp5 or None, 6: exp6 or None, 7: exp7 or None, 8: exp8 or None,
            }
            cfg = QAConfig(
                start_url=start_url,
                second_url=second_url,
                third_url=third_url,
                ga4_pattern=ga4_pattern,
                accept_selector=accept_selector,
                link_selector_2=link_selector_2,
                link_selector_4=link_selector_4,
                link_selector_7=link_selector_7,
                headless=headless,
                slow_mo_ms=slow_mo_ms,
                action_wait_ms=action_wait_ms,
                load_wait_ms=load_wait_ms,
                capture_screenshots=capture_screenshots,
                expected_groups=expected_groups,
            )

            status_placeholder = st.empty()

            def progress_cb(msg):
                status_placeholder.info(msg)

            with st.spinner("Running QA suite..."):
                try:
                    results = run_qa(cfg, progress_cb=progress_cb)
                    st.session_state.qa_results = results
                    st.session_state.qa_ran_at = datetime.now().isoformat(timespec="seconds")
                    status_placeholder.empty()
                except Exception as e:
                    status_placeholder.empty()
                    st.error(f"QA run failed: {e}")

    results = st.session_state.qa_results
    if results:
        st.caption(f"Last run: {st.session_state.qa_ran_at}")

        summary_df = build_summary_df(results)
        pass_count = (summary_df["Status"] == "PASS").sum()
        fail_count = (summary_df["Status"] == "FAIL").sum()
        error_count = (summary_df["Status"] == "ERROR").sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Steps run", len(results))
        c2.metric("Passed", int(pass_count))
        c3.metric("Failed", int(fail_count))
        c4.metric("Errors", int(error_count))

        st.subheader("Summary")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇ Download full report (JSON)",
            data=results_to_json(results),
            file_name=f"onetrust_qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

        st.subheader("Step details")
        for res in results:
            render_step(res)
    else:
        st.info("Configure the URLs in the sidebar and click **Run QA Suite** to begin.")


if __name__ == "__main__":
    main()
