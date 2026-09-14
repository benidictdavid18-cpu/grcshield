"""Capture the README screenshots from a running instance.

Drives the installed Microsoft Edge through Playwright, so nothing is downloaded. The
first four are taken as the read-only auditor, because the role chip in the masthead is
part of what they are meant to show. The last two are taken as the ISMS manager: a write
the API refuses, and the change history a write leaves behind. The second of those
re-scores RISK-004 and restores it, so run this against a scratch database rather than
one whose trail you want to keep.

    pip install playwright          # not in requirements-dev: only this script needs it
    python scripts/capture_screenshots.py --base-url http://localhost:5199

Requires the app to be running. Writes PNGs into docs/screenshots/.
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
AUDITOR = ("auditor", "auditor-demo-2026")
MANAGER = ("isms.manager", "manager-demo-2026")

# Wide enough that the SoA drawer sits beside the table rather than under it, and tall
# enough that the KRI grid does not need scrolling.
VIEWPORT = {"width": 1600, "height": 1000}


def sign_in(page, base: str, account: tuple[str, str] = AUDITOR) -> None:
    page.goto(f"{base}/", wait_until="networkidle")
    page.fill("#username", account[0])
    page.fill("#password", account[1])
    page.click("button.primary")
    page.wait_for_selector(".masthead", timeout=15_000)


def sign_out(page) -> None:
    page.click(".session button")
    page.wait_for_selector("#username", timeout=10_000)


def shot(page, name: str, *, full: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=full)
    size_kb = round(path.stat().st_size / 1024)
    print(f"  {path.name:20} {size_kb:>5} KB{'  (full page)' if full else ''}")


def element_shot(page, selector: str, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.png"
    page.locator(selector).scroll_into_view_if_needed()
    page.locator(selector).screenshot(path=str(path))
    print(f"  {path.name:20} {round(path.stat().st_size / 1024):>5} KB  (element)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5199")
    base = parser.parse_args().base_url.rstrip("/")

    print(f"Capturing from {base}\n")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # crisp on a high-DPI display
            color_scheme="dark",
        ).new_page()

        sign_in(page, base)

        # 1. Risk detail — the whole calculation chain, so full page.
        page.goto(f"{base}/risks/RISK-004", wait_until="networkidle")
        page.wait_for_selector(".chain")
        shot(page, "risk-004", full=True)

        # 2. SoA — filtered to A.8.5 with the traceability drawer open.
        #
        # The drawer is position:sticky with a max-height of the viewport and its own
        # scrollbar, so a full-page capture clips the chain rather than expanding it.
        # A taller viewport is the honest fix: this is what the page looks like on a
        # screen that fits it, not a doctored DOM.
        page.set_viewport_size({"width": 1600, "height": 2300})
        page.goto(f"{base}/soa", wait_until="networkidle")
        page.wait_for_selector(".control-group")
        page.fill('input[type="search"]', "A.8.5")
        page.wait_for_timeout(400)
        page.click(".cell-ref button")
        page.wait_for_selector(".soa-drawer .chain-steps", timeout=10_000)
        page.wait_for_timeout(600)
        shot(page, "soa")
        page.set_viewport_size(VIEWPORT)

        # 3. KRI dashboard, with one definition expanded to show the formula.
        page.goto(f"{base}/dashboard", wait_until="networkidle")
        page.wait_for_selector(".kri-grid")
        page.click(".kri-card .kri-toggle")
        page.wait_for_selector(".kri-definition")
        page.wait_for_timeout(300)
        shot(page, "dashboard")

        # 4. Executive summary — posture statement and the three priorities.
        page.goto(f"{base}/executive", wait_until="networkidle")
        page.wait_for_selector(".priorities li")
        page.wait_for_timeout(300)
        shot(page, "executive")

        # The last two need a role that can write.
        sign_out(page)
        sign_in(page, base, MANAGER)

        # 5. A write the API refuses. RISK-019 has every control untested, so claiming
        #    a reduction below inherent is refused in the API's own words. Nothing is
        #    validated in the browser; the form shows what the API said.
        page.goto(f"{base}/risks/RISK-019", wait_until="networkidle")
        page.wait_for_selector(".chain")
        page.click(".edit-panel .ai-toggle")
        page.select_option('select[name="residual_likelihood"]', "1")
        page.fill('textarea[name="residual_justification"]', "Claiming a reduction anyway.")
        page.click(".edit-form button[type=submit]")
        page.wait_for_selector(".edit-form .banner", timeout=10_000)
        page.wait_for_timeout(300)
        element_shot(page, ".edit-panel", "refusal")

        # 6. The change history. Re-score RISK-004 and put it back: two events, actor
        #    and before/after on each, readable by every role.
        page.goto(f"{base}/risks/RISK-004", wait_until="networkidle")
        page.wait_for_selector(".chain")
        original = page.locator(".justification p").inner_text()
        for likelihood, justification in (
            ("2", "Privileged MFA enrolment reached 100% on 2026-09-01; AC-002 re-tested clean."),
            ("3", original),
        ):
            page.click(".edit-panel .ai-toggle")
            page.select_option('select[name="residual_likelihood"]', likelihood)
            page.fill('textarea[name="residual_justification"]', justification)
            page.click(".edit-form button[type=submit]")
            page.wait_for_selector(".history-list li", timeout=10_000)
            page.wait_for_timeout(400)
        page.click(".history-list li:nth-child(2) .history-toggle")
        page.wait_for_selector(".history-diff")
        page.wait_for_timeout(300)
        element_shot(page, ".history", "change-history")

        browser.close()

    print(f"\nWrote 6 screenshots to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
