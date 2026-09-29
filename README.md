# 694,000 Steps for October - live tracker

A static page (`index.html`) showing a live step count, updated hourly from Garmin Connect by a GitHub Action.

## 1. Personalise it
Edit `config.json`: your name, charity, **donate_url**, Instagram link, **timezone** (e.g. `Australia/Sydney`, `America/New_York`), and the optional per-day `dedications`.

## 2. Put it on GitHub
1. Create a new **public** repository on GitHub (e.g. `694-steps`).
2. Upload this folder's contents to it (GitHub Desktop, or drag-and-drop in the web UI).
3. Repo **Settings > Pages > Build and deployment**: Source = "Deploy from a branch", branch `main`, folder `/ (root)`.
4. Your page will be live at `https://<your-username>.github.io/694-steps/`.

## 3. Connect Garmin (do this on your own computer)
1. Install Python 3.10+ and run: `pip install -r requirements.txt`
2. Run `python scripts/login_once.py`. Type your Garmin email, password and MFA code (if asked) when prompted. It prints a long token.
3. In the repo: **Settings > Secrets and variables > Actions > New repository secret**. Name: `GARMIN_TOKENS`, value: the token.
4. **Actions tab > Update steps > Run workflow** to test it. Green tick = `data/steps.json` now holds real data. The sample-data banner disappears automatically.

The workflow then runs hourly on its own. Your password is never stored anywhere.

## If something breaks
- **Workflow fails / Garmin blocks GitHub's servers:** run `python scripts/fetch_steps.py` on your own PC (set `GARMIN_TOKENS` in your environment first) on an hourly Windows scheduled task, then push `data/steps.json`.
- **Any day is wrong or missing:** put the correct number in `data/manual.json`, e.g. `{"2026-10-05": 25000}`. It overrides Garmin for that day.
- **Numbers look stale:** the page can only be as fresh as your last watch sync. Open the Garmin Connect app on your phone to force one.

## Preview locally
`python -m http.server 8694` then open http://localhost:8694
