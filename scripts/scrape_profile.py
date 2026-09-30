"""Turn your PUBLIC Garmin Connect profile's lifetime step total into daily steps.

Run it on your own PC (hourly, via Task Scheduler). Each run:
  1. opens the profile in a headless browser and reads "Lifetime Totals > Steps"
  2. stores a snapshot in data/lifetime.json (only when the number changed)
  3. rebuilds data/steps.json: steps(day) = lifetime at end of day - lifetime at end of previous day
     (the baseline is the last snapshot before the walk starts; data/manual.json overrides win)
  4. commits and pushes so the live page updates

    py scripts/scrape_profile.py            # read, rebuild, publish
    py scripts/scrape_profile.py --no-push  # read and rebuild only

Needs:  py -m pip install playwright   (uses the Microsoft Edge already on Windows)
Requires the profile to be public and to show lifetime step totals.
"""
import argparse
import json
import re
import subprocess
import sys
import time as _time
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
LIFETIME = ROOT / "data" / "lifetime.json"
MANUAL = ROOT / "data" / "manual.json"
STEPS = ROOT / "data" / "steps.json"
TZ = ZoneInfo(CFG["timezone"])


def launch_browser(p):
    """Try Edge, then Chrome, then Playwright's own Chromium; retry each once."""
    errors = []
    for kwargs in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
        for _ in range(2):
            try:
                return p.chromium.launch(headless=True, **kwargs)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{kwargs or 'bundled chromium'}: {str(e).strip().splitlines()[0]}")
                _time.sleep(3)
    raise RuntimeError("Could not start a browser:\n  " + "\n  ".join(errors))


def read_lifetime_steps(url: str) -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = launch_browser(p)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("text=Lifetime Totals", timeout=60000)
            try:  # the numbers load after the heading
                page.wait_for_function(
                    r"() => /Steps\s*[\d,]{4,}\s*Steps/.test((document.body.innerText.split('Lifetime Totals')[1]) || '')",
                    timeout=45000,
                )
            except Exception:
                pass  # fall through: the check below reports what the page showed
            text = page.inner_text("body")
        finally:
            browser.close()
    section = text.split("Lifetime Totals", 1)[1]
    m = re.search(r"Steps\s*([\d,]+)\s*Steps", section)
    if not m:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "logs" / "last_page.txt").write_text(text, encoding="utf-8")
        raise RuntimeError("Could not find lifetime Steps on the profile page (is it public?).")
    return int(m.group(1).replace(",", ""))


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def value_at(snaps: list[dict], cutoff: datetime):
    """Lifetime steps at the last snapshot strictly before cutoff (None if there is none)."""
    best = None
    for s in snaps:
        if datetime.fromisoformat(s["t"]) < cutoff:
            best = s["steps"]
    return best


def build_days(snaps: list[dict], now: datetime) -> list[dict]:
    start = date.fromisoformat(CFG["start"])
    end = date.fromisoformat(CFG["end"])
    if now.date() < start or not snaps:
        return []
    midnight = lambda d: datetime.combine(d, time.min, tzinfo=TZ)
    prev = value_at(snaps, midnight(start))
    if prev is None:
        prev = snaps[0]["steps"]
        print("Warning: no snapshot before the walk started - steps before the first run are missed.")
    manual = load(MANUAL, {})
    days, cursor = [], start
    last = min(end, now.date())
    while cursor <= last:
        cur = value_at(snaps, midnight(cursor + timedelta(days=1))) if cursor < now.date() else snaps[-1]["steps"]
        if cur is None:
            cur = prev
        key = cursor.isoformat()
        days.append({"date": key, "steps": manual.get(key, max(0, cur - prev))})
        prev = max(prev, cur)
        cursor += timedelta(days=1)
    return days


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    url = CFG.get("garmin_profile")
    if not url:
        print("config.json has no garmin_profile URL.")
        return 1
    now = datetime.now(TZ)
    total = read_lifetime_steps(url)
    print(f"Lifetime steps on profile: {total:,}")

    store = load(LIFETIME, {"snapshots": []})
    snaps = store["snapshots"]
    if not snaps or snaps[-1]["steps"] != total:
        snaps.append({"t": now.isoformat(timespec="seconds"), "steps": total})
        LIFETIME.write_text(json.dumps(store, indent=1) + "\n", encoding="utf-8")

    days = build_days(snaps, now)
    STEPS.write_text(
        json.dumps({"updated": now.isoformat(timespec="seconds"), "days": days}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(days)} day(s), total {sum(d['steps'] for d in days):,} steps this walk.")

    if a.no_push:
        return 0
    git("add", "data/lifetime.json", "data/steps.json")
    if subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=ROOT).returncode == 0:
        print("Nothing changed - not publishing.")
        return 0
    git("commit", "-m", f"Steps update {now:%Y-%m-%d %H:%M}")
    git("pull", "--rebase", "-q")
    git("push", "-q")
    print("Published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
