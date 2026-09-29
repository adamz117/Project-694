"""Manual backup: record a day's steps (plus an optional proof screenshot) and publish.

    py scripts/add_steps.py 24500                              # today's steps
    py scripts/add_steps.py 24500 --date 2026-10-03            # a specific day
    py scripts/add_steps.py 24500 --proof "C:/path/shot.png"   # attach proof screenshot
    py scripts/add_steps.py 24500 --no-push                    # update files only

Writes data/manual.json (so a later Garmin sync keeps your number), rebuilds
data/steps.json, copies any proof image to proof/<date>.<ext> and lists it in
data/proofs.json, then commits and pushes so the live page updates.
"""
import argparse
import json
import shutil
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
MANUAL = ROOT / "data" / "manual.json"
STEPS = ROOT / "data" / "steps.json"
PROOFS = ROOT / "data" / "proofs.json"
PROOF_DIR = ROOT / "proof"


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("steps", type=int)
    p.add_argument("--date", help="YYYY-MM-DD (default: today in your timezone)")
    p.add_argument("--proof", help="path to a screenshot to show on the site as proof")
    p.add_argument("--no-push", action="store_true")
    a = p.parse_args()

    tz = ZoneInfo(CFG["timezone"])
    now = datetime.now(tz)
    day = a.date or now.date().isoformat()
    start = date.fromisoformat(CFG["start"])
    end = date.fromisoformat(CFG["end"])
    if not start <= date.fromisoformat(day) <= end:
        raise SystemExit(f"{day} is outside the walk ({start} to {end}).")

    manual = load(MANUAL, {})
    manual[day] = a.steps
    save(MANUAL, manual)

    # Keep any real (non-sample) data already in steps.json; manual values win.
    existing = {}
    old = load(STEPS, {})
    if old and not old.get("sample"):
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

    to_add = ["data/steps.json", "data/manual.json"]
    if a.proof:
        src = Path(a.proof)
        if not src.is_file():
            raise SystemExit(f"Proof image not found: {src}")
        PROOF_DIR.mkdir(exist_ok=True)
        dest = PROOF_DIR / f"{day}{src.suffix.lower()}"
        shutil.copyfile(src, dest)
        proofs = load(PROOFS, {})
        proofs[day] = f"proof/{dest.name}"
        save(PROOFS, proofs)
        to_add += ["data/proofs.json", f"proof/{dest.name}"]
        print(f"Proof saved as {dest.relative_to(ROOT)}")

    if a.no_push:
        return
    subprocess.run(["git", "add", *to_add], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"Steps for {day}"], cwd=ROOT, check=True)
    subprocess.run(["git", "pull", "--rebase", "-q"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)
    print("Published. The live page updates within a minute or two.")


if __name__ == "__main__":
    main()
