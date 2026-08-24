"""
Estonia MFA consular booking watcher.

Selects New Delhi in the representation dropdown, waits for the service
dropdown to populate, and reports whether "Application for Residence Permit"
(or any option containing "residence permit") is available.

Notifies via Telegram. Designed to run on GitHub Actions on a schedule.
Your laptop is not involved.

Secrets (set in GitHub -> Settings -> Secrets and variables -> Actions):
  TG_TOKEN    your (revoked-and-regenerated) bot token
  TG_CHAT_ID  your numeric chat id from @userinfobot
"""

import os
import sys
import requests
from playwright.sync_api import sync_playwright

URL = "https://broneering.mfa.ee/en/"
REPRESENTATION = "Embassy of the Republic of Estonia in New Delhi"
PERSONS = "1"
# Services to watch for (case-insensitive substrings). Add more lines any time.
MATCHES = [
    "residence permit",
    "d-visa",
]

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# When true, send a Telegram message every run listing what options were seen,
# so you can confirm it's reading the right dropdown. Turn off once confirmed.
DEBUG_LIST = os.environ.get("DEBUG_LIST", "true").lower() == "true"

# When true, send an hourly "still watching, nothing yet" heartbeat.
HEARTBEAT = os.environ.get("HEARTBEAT", "false").lower() == "true"


def send(text):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("No Telegram credentials set; would have sent:\n" + text)
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": text},
            timeout=30,
        )
        print("Telegram status:", r.status_code, r.text[:200])
    except Exception as e:
        print("Telegram send failed:", e)


def get_service_options(page):
    """Return list of visible option texts from the service dropdown.

    The page has two <select> elements up front (representation, persons).
    After choosing New Delhi, a service <select> populates. We locate it as
    the select whose options mention a consular service rather than a country
    or a number.
    """
    selects = page.query_selector_all("select")
    best = []
    for sel in selects:
        opts = [o.inner_text().strip() for o in sel.query_selector_all("option")]
        opts = [o for o in opts if o]  # drop blanks
        joined = " ".join(opts).lower()
        # skip the representation select (full of "embassy"/"consular mission")
        # and the persons select (just numbers)
        if "embassy of the republic" in joined:
            continue
        if opts and all(o.strip().isdigit() for o in opts):
            continue
        # candidate service select
        if len(opts) > len(best):
            best = opts
    return best


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(45000)
        page.goto(URL, wait_until="networkidle")

        # 1) choose representation (first select on the page)
        selects = page.query_selector_all("select")
        if not selects:
            send("Estonia watcher: page had no dropdowns; site layout may have changed.")
            browser.close()
            sys.exit(1)

        rep = selects[0]
        try:
            rep.select_option(label=REPRESENTATION)
        except Exception:
            # fall back to partial match on New Delhi
            for o in rep.query_selector_all("option"):
                if "new delhi" in o.inner_text().strip().lower():
                    rep.select_option(value=o.get_attribute("value"))
                    break

        # 2) let the service dropdown populate (JS reaction)
        page.wait_for_timeout(2500)
        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass

        # 3) try to set persons if such a select exists (harmless if not needed)
        for sel in page.query_selector_all("select"):
            opts = [o.inner_text().strip() for o in sel.query_selector_all("option")]
            if opts and all(o.isdigit() for o in opts if o):
                try:
                    sel.select_option(value=PERSONS)
                except Exception:
                    pass
                break

        page.wait_for_timeout(1500)

        # 4) read the service dropdown
        options = get_service_options(page)
        print("Service options seen:", options)

        # find which watched services are currently available
        hits = []
        for opt in options:
            for m in MATCHES:
                if m in opt.lower():
                    hits.append(opt)
                    break

        if hits:
            opened = "\n".join("- " + h for h in hits)
            send(
                "SLOT OPEN (New Delhi)\n\n"
                "These watched service(s) are now selectable:\n"
                + opened
                + "\n\nGo book manually now:\n"
                + URL
            )
            print("MATCH FOUND -> alerted:", hits)
        else:
            print("Not available yet.")
            if DEBUG_LIST:
                listing = "\n".join("- " + o for o in options) or "(none read)"
                send(
                    "Estonia watcher heartbeat (New Delhi).\n"
                    "Residence Permit not open yet. Options currently seen:\n"
                    + listing
                    + "\n\n(Reply here once confirmed and I'll silence these.)"
                )
            elif HEARTBEAT:
                from datetime import datetime, timezone, timedelta
                # A manual "Run workflow" click always pings, so a manual test
                # always gives you Telegram proof.
                manual = os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"
                # IST = UTC + 5:30. One "still watching" ping a day, in the 2pm
                # IST hour. Window is the first 15 min so it fires reliably even
                # when GitHub delays runs (you'll get ~3 pings across those 15
                # min at 5-min cadence, once per day).
                ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                scheduled = ist.hour == 14 and ist.minute < 15
                if manual or scheduled:
                    send(
                        "Estonia watcher: still running, no residence "
                        "permit slot for New Delhi yet."
                    )

        browser.close()


if __name__ == "__main__":
    run()
