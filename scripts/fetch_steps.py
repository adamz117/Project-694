"""Fetch October step counts from Garmin Connect and write data/steps.json.

Auth (first match wins):
  GARMIN_TOKENS               token string from scripts/login_once.py (preferred)
  GARMIN_EMAIL + GARMIN_PASSWORD

Manual overrides in data/manual.json ({"2026-10-05": 25000}) replace Garmin's value for that day.
On any failure the script exits non-zero and leaves the existing steps.json untouched.
"""
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from garminconnect import Garmin

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
MANUAL_PATH = ROOT / "data" / "manual.json"
OUT_PATH = ROOT / "data" / "steps.json"
CHUNK_DAYS = 28  # Garmin limits the range of a single daily-steps request


def login() -> Garmin:
    tokens = os.environ.get("GARMIN_TOKENS")
    if tokens:
        client = Garmin()
        client.login(tokens)
        return client
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login()
    return client


def fetch_days(client: Garmin, start: date, end: date) -> dict[str, int]:
    steps: dict[str, int] = {}
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS - 1), end)
        for row in client.get_daily_steps(cursor.isoformat(), chunk_end.isoformat()):
            steps[row["calendarDate"]] = int(row.get("totalSteps") or 0)
        cursor = chunk_end + timedelta(days=1)
    return steps


def main() -> int:
    tz = ZoneInfo(CFG["timezone"])
    now = datetime.now(tz)
    start = date.fromisoformat(CFG["start"])
    end = min(date.fromisoformat(CFG["end"]), now.date())
    if end < start:
        print("Walk has not started yet - nothing to fetch.")
        return 0

    if not any(os.environ.get(k) for k in ("GARMIN_TOKENS", "GARMIN_EMAIL")):
        print("No Garmin credentials configured - skipping (manual mode).")
        return 0

    steps = fetch_days(login(), start, end)
    steps.update(json.loads(MANUAL_PATH.read_text(encoding="utf-8")) if MANUAL_PATH.exists() else {})

    days = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        days.append({"date": key, "steps": steps.get(key, 0)})
        cursor += timedelta(days=1)

    OUT_PATH.write_text(
        json.dumps({"updated": now.isoformat(timespec="seconds"), "days": days}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(days)} days, total {sum(d['steps'] for d in days):,} steps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
