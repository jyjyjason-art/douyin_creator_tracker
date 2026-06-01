---
name: douyin-creator-tracker
description: Use this skill when maintaining or running the local Douyin creator video and commerce tracker that connects to an existing Google Chrome CDP session, collects creator profile videos, extracts product_name and real product_id, writes Excel outputs, and resumes from checkpoints.
---

# Douyin Creator Tracker Skill

## When to use

Use this skill for:

```text
C:\cutting video\douyin_creator_tracker
```

Typical requests:

- Run a Douyin creator profile collection.
- Run daily incremental checks without full profile scan every time.
- Continue after network or CDP interruption.
- Debug missing `product_id`.
- Validate an Excel output.
- Update project workflow or runbook.
- Adjust humanized browser behavior.
- Use the local web console to start/stop collection and inspect logs.

## Rules

- Do not use Playwright to create a browser.
- Use Google Chrome Stable launched with CDP.
- Reuse the user's logged-in Chrome profile.
- Reuse one Douyin tab sequentially where possible.
- Up to 5 tabs is acceptable only when necessary.
- Do not click payment, follow, private message, or account-changing actions.
- Keep `outputs/` and `evidence/` local; do not commit them.
- Keep Windows awake during long collection runs.
- Daily strategy:
  - Existing creator: prefer `--all --incremental` with smart window.
  - New creator: allow automatic full scan fallback.

## Standard Commands

Validate code:

```powershell
cd "C:\cutting video\douyin_creator_tracker"
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py keep_awake.py
```

Single creator:

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --incremental-daily-max 10 --incremental-lookback-days 1 --out "outputs\douyin_creator.xlsx" --evidence-dir "evidence\douyin_creator" --retries 2 --close-extra-tabs --max-tabs 3
```

Multiple creators:

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --incremental-daily-max 10 --incremental-lookback-days 1 --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 2 --close-extra-tabs --max-tabs 3
```

Web console:

```powershell
python web_app.py
```

## Resume Behavior

The project supports checkpoint resume:

- Excel is written after each video.
- `outputs/collected_index.json` is updated after each video.
- Re-running the same command with `--incremental` skips collected `video_id`s.

It does not yet include an always-on external runner that restarts Python automatically after process exit.

Smart incremental window:

- Active when `--all --incremental` and not disabled.
- Window size = `(days_since_last_collect + incremental_lookback_days) * incremental_daily_max`.
- New creator in index falls back to full scan.

## Validation

After a run, read the Excel and report:

- rows
- unique videos
- status counts
- missing `product_id`
- duplicate video rows
- output path

## Known Data Sources

- Profile video list: `/aweme/v1/web/aweme/post/`, top-level `aweme_list`.
- Video detail and product anchor: `/aweme/v1/web/aweme/detail`, `anchorInfo.extra`.
- Product detail fallback: `/ecom/product/detail/saas/pc`.

## Important Distinction

The page config `a11y-configs product_id:100005` is accessibility SDK config, not commerce product ID.
