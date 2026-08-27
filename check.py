"""
Estonia MFA consular booking watcher for D-Visa (New Delhi).
Watches specifically for "Long-stay visa (D-visa) application".
"""

import os
import sys
import requests
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

URL = "https://broneering.mfa.ee/en/"
REPRESENTATION = "Embassy of the Republic of Estonia in New Delhi"
PERSONS = "1"

# Target search phrases for D-Visa
TARGET_KEYWORDS = [
    "long-stay visa (d-visa) application",
    "long-stay visa (d-visa)",
    "d-visa application",
    "d-visa",
    "long-stay visa",
]

TG_TOKEN = os.environ.get("TG_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()
DEBUG_LIST = os.environ.get("DEBUG_LIST", "false").lower() == "true"
HEARTBEAT = os.environ.get("HEARTBEAT", "true").lower() == "true"


def send(text: str):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("[Warning] Telegram credentials missing. Message not sent:\n" + text)
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": text}
        r = requests.post(url, data=payload, timeout=20)
        res = r.json()
        if not res.get("ok"):
            print(f"[Telegram Error] {res.get('error_code')}: {res.get('description')}")
        else:
            print("[Telegram] Status/Alert message sent successfully.")
    except Exception as e:
        print(f"[Telegram Error] Request failed: {e}")


def get_service_options(page):
    selects = page.query_selector_all("select")
    best_options = []

    for sel in selects:
        opts = [o.inner_text().strip() for o in sel.query_selector_all("option")]
        opts = [o for o in opts if o]
        joined = " ".join(opts).lower()

        if "embassy of the republic" in joined or "consular mission" in joined:
            continue
        if opts and all(o.strip().isdigit() for o in opts):
            continue

        if len(opts) > len(best_options):
            best_options = opts

    return best_options


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)

        print(f"Checking {URL}...")
        page.goto(URL, wait_until="networkidle")

        selects = page.query_selector_all("select")
        if not selects:
            send("⚠️ Estonia Watcher Alert: Portal dropdowns not found. The site layout may have changed.")
            browser.close()
            sys.exit(1)

        # 1. Select New Delhi Representation
        rep_select = selects[0]
        selected = False
        try:
            rep_select.select_option(label=REPRESENTATION)
            selected = True
        except Exception:
            for o in rep_select.query_selector_all("option"):
                if "new delhi" in o.inner_text().strip().lower():
                    rep_select.select_option(value=o.get_attribute("value"))
                    selected = True
                    break

        # 2. Wait for reactive option load
        page.wait_for_timeout(3000)
        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass

        # 3. Handle person count
        for sel in page.query_selector_all("select"):
            opts = [o.inner_text().strip() for o in sel.query_selector_all("option")]
            if opts and all(o.isdigit() for o in opts if o):
                try:
                    sel.select_option(value=PERSONS)
                except Exception:
                    pass
                break

        page.wait_for_timeout(2000)

        # 4. Read active options
        options = get_service_options(page)
        print("Visible Service Options:", options)

        hits = []
        for opt in options:
            opt_lower = opt.lower()
            if any(k in opt_lower for k in TARGET_KEYWORDS):
                hits.append(opt)

        # 5. Notifications
        if hits:
            opened_str = "\n".join("- " + h for h in hits)
            send(
                "🚨 ESTONIA D-VISA SLOT OPEN (New Delhi) 🚨\n\n"
                "The requested service is now available in the dropdown:\n"
                f"{opened_str}\n\n"
                f"Book immediately at:\n{URL}"
            )
            print(f"[Match Found] Alert sent for: {hits}")
        else:
            print("D-Visa appointment option is not currently listed.")

            if DEBUG_LIST:
                listing = "\n".join("- " + o for o in options) if options else "(No services visible)"
                send(
                    "🔍 Estonia Watcher (Debug Report - New Delhi)\n\n"
                    "D-Visa option is not open. Current visible dropdown entries:\n"
                    f"{listing}"
                )
            elif HEARTBEAT:
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                is_manual = os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"
                
                # Triggers between 14:00 and 14:20 IST (2:00 PM to 2:20 PM)
                is_daily_2pm_window = (now_ist.hour == 14 and now_ist.minute < 20)

                if is_manual or is_daily_2pm_window:
                    listing = "\n".join("- " + o for o in options) if options else "(No services visible)"
                    time_str = now_ist.strftime("%d %b %Y, %I:%M %p IST")
                    send(
                        f"📊 Daily Status Report ({time_str})\n\n"
                        "Status: Watcher running normally.\n"
                        "D-Visa Slots: ❌ Not open yet.\n\n"
                        f"Current visible options:\n{listing}"
                    )

        browser.close()


if __name__ == "__main__":
    run()
