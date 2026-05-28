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
- Continue after network or CDP interruption.
- Debug missing `product_id`.
- Validate an Excel output.
- Update project workflow or runbook.
- Adjust humanized browser behavior.

## Rules

- Do not use Playwright to create a browser.
- Use Google Chrome Stable launched with CDP.
- Reuse the user's logged-in Chrome profile.
- Reuse one Douyin tab sequentially where possible.
- Up to 5 tabs is acceptable only when necessary.
- Do not click payment, follow, private message, or account-changing actions.
- Keep `outputs/` and `evidence/` local; do not commit them.
- Keep Windows awake during long collection runs.

## Standard Commands

Validate code:

```powershell
cd "C:\cutting video\douyin_creator_tracker"
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py keep_awake.py
```

Single creator:

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --out "outputs\douyin_creator.xlsx" --evidence-dir "evidence\douyin_creator" --retries 2 --close-extra-tabs --max-tabs 3
```

Multiple creators:

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 2 --close-extra-tabs --max-tabs 3
```

## Resume Behavior

The project supports checkpoint resume:

- Excel is written after each video.
- `outputs/collected_index.json` is updated after each video.
- Re-running the same command with `--incremental` skips collected `video_id`s.

It does not yet include an always-on external runner that restarts Python automatically after process exit.

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
