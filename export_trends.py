"""Exports Google Trends "Trending now" as the raw CSV via the page's own Export button.

Writes trends/<GEO>/latest.csv (only on success) and trends/<GEO>/meta.json (always),
so the Magnetic Newsdesk app can tell a fresh file from a stale or failed one.
"""

import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

GEO = os.environ.get("TRENDS_GEO", "US")
HOURS = os.environ.get("TRENDS_HOURS", "168")
MIN_ROWS = int(os.environ.get("TRENDS_MIN_ROWS", "100"))
ATTEMPTS = 3
URL = f"https://trends.google.com/trending?geo={GEO}&hours={HOURS}"

OUT_DIR = Path("trends") / GEO
CSV_PATH = OUT_DIR / "latest.csv"
META_PATH = OUT_DIR / "meta.json"
DEBUG_DIR = Path("debug")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def download_csv(attempt):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, locale="en-US", timezone_id="UTC")
        page = context.new_page()
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            export = page.get_by_text("Export", exact=True).first
            export.wait_for(state="visible", timeout=60_000)
            export.click()
            menu_item = page.get_by_role("menuitem", name="Download CSV")
            menu_item.wait_for(state="visible", timeout=15_000)
            with page.expect_download(timeout=60_000) as download_info:
                menu_item.click()
            return Path(download_info.value.path()).read_bytes()
        except Exception:
            DEBUG_DIR.mkdir(exist_ok=True)
            page.screenshot(path=str(DEBUG_DIR / f"attempt-{attempt}.png"), full_page=True)
            raise
        finally:
            browser.close()


def validate(raw):
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or not rows[0] or not rows[0][0].strip().lower().startswith("trend"):
        raise ValueError(f"Unexpected CSV header: {rows[0] if rows else 'empty file'}")
    data_rows = len(rows) - 1
    if data_rows < MIN_ROWS:
        raise ValueError(f"Only {data_rows} rows (expected at least {MIN_ROWS})")
    return data_rows, rows[0]


def read_meta():
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_meta(meta):
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = read_meta()
    meta.update({"geo": GEO, "hours": int(HOURS), "source_url": URL, "last_attempt_at": now_iso()})

    last_error = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            raw = download_csv(attempt)
            row_count, header = validate(raw)
            CSV_PATH.write_bytes(raw)
            meta.update({
                "status": "ok",
                "fetched_at": meta["last_attempt_at"],
                "row_count": row_count,
                "columns": header,
                "error": None,
            })
            write_meta(meta)
            print(f"Saved {row_count} rows to {CSV_PATH}")
            return 0
        except Exception as err:
            last_error = f"{type(err).__name__}: {err}"
            print(f"Attempt {attempt}/{ATTEMPTS} failed: {last_error}", file=sys.stderr)
            if attempt < ATTEMPTS:
                time.sleep(30 * attempt)

    meta.update({"status": "failed", "error": last_error[:500]})
    write_meta(meta)
    return 1


if __name__ == "__main__":
    sys.exit(main())
