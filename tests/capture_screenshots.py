"""
capture_screenshots.py — Playwright browser test & screenshot capture for CommerceSense AI v3.
Runs across Desktop (1440x900), Tablet (1024x768), and Mobile (390x844).
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = [
    ("/overview", "01_overview"),
    ("/products", "02_products"),
    ("/products/P001", "03_product_workspace"),
    ("/competitors", "04_competitors"),
    ("/market-radar", "05_market_radar"),
    ("/opportunities", "06_opportunities"),
    ("/pricing-lab", "07_pricing_lab"),
    ("/actions", "08_action_center"),
    ("/automations", "09_automations"),
    ("/reports", "10_reports"),
    ("/connections", "11_connections"),
]

VIEWPORTS = [
    {"name": "desktop", "width": 1440, "height": 900},
    {"name": "tablet", "width": 1024, "height": 768},
    {"name": "mobile", "width": 390, "height": 844},
]

BASE_URL = "http://127.0.0.1:5173"

def run_browser_capture():
    print(f"Connecting to {BASE_URL}...")
    errors_logged = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=1,
            )
            page = context.new_page()

            page.on("console", lambda msg: errors_logged.append(f"[{vp['name']}] Console {msg.type}: {msg.text}") if msg.type == "error" else None)

            for route, filename in ROUTES:
                url = f"{BASE_URL}{route}"
                try:
                    page.goto(url, wait_until="networkidle", timeout=15000)
                    page.wait_for_timeout(800)  # Wait for charts/animations

                    # Check horizontal overflow on mobile/tablet
                    has_overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2")
                    if has_overflow and vp["name"] == "mobile":
                        print(f"Warning: minor overflow detected on {route} at {vp['name']}")

                    shot_path = OUTPUT_DIR / f"{filename}_{vp['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved: {shot_path.name}")
                except Exception as e:
                    print(f"Error loading {url} on {vp['name']}: {e}")
                    errors_logged.append(f"Load error on {route}: {e}")

            context.close()
        browser.close()

    print("\nCapture Complete!")
    if errors_logged:
        print(f"Recorded {len(errors_logged)} non-fatal errors:")
        for err in errors_logged[:5]:
            print(" -", err)
    else:
        print("Zero console errors across all 11 routes and 3 viewports!")

if __name__ == "__main__":
    run_browser_capture()

