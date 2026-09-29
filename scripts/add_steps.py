"""Manual backup: record a day's steps from your watch and publish the tracker.

    py scripts/add_steps.py 24500               # sets TODAY's steps
    py scripts/add_steps.py 24500 --date 2026-10-03
    py scripts/add_steps.py 24500 --no-push     # update files only, don't publish

Writes data/manual.json (so the Garmin sync keeps your number) and rebuilds
data/steps.json, then commits and pushes so the live page updates.
"""
import argparse
import json
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
MANUAL = ROOT / "data" / "manual.json"
STEPS = ROOT / "data" / "steps.json"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("steps", type=int)
    p.add_argument("--date", help="YYYY-MM-DD (default: today in your timezone)")
    p.add_argument("--no-push", action="store_true")
    a = p.parse_args()

    tz = ZoneInfo(CFG["timezone"])
    now = datetime.now(tz)
    day = a.date or now.date().isoformat()
    start = date.fromisoformat(CFG["start"])
    end = date.fromisoformat(CFG["end"])
    if not start <= date.fromisoformat(day) <= end:
        raise SystemExit(f"{day} is outside the walk ({start} to {end}).")

    manual = json.loads(MANUAL.read_text(encoding="utf-8")) if MANUAL.exists() else {}
    manual[day] = a.steps
    MANUAL.write_text(json.dumps(manual, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Keep any real (non-sample) data already in steps.json; manual values win.
    existing = {}
    if STEPS.exists():
        old = json.loads(STEPS.read_text(encoding="utf-8"))
        if not old.get("sample"):
            existing = {d["date"]: d["steps"] for d in old["days"]}
    existing.update(manual)

    last = max(date.fromisoformat(k) for k in existing)
    days, cursor = [], start
    while cursor <= last:
        k = cursor.isoformat()
        days.append({"date": k, "steps": existing.get(k, 0)})
        cursor += timedelta(days=1)
    STEPS.write_text(
        json.dumps({"updated": now.isoformat(timespec="seconds"), "days": days}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{day}: {a.steps:,} steps. Total so far: {sum(d['steps'] for d in days):,}")

    if a.no_push:
        return
    subprocess.run(["git", "add", "data/steps.json", "data/manual.json"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"Steps for {day}"], cwd=ROOT, check=True)
    subprocess.run(["git", "pull", "--rebase", "-q"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)
    print("Published. The live page updates within a minute or two.")


if __name__ == "__main__":
    main()
