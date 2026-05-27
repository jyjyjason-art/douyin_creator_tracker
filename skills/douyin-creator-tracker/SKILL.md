---
name: douyin-creator-tracker
description: Use this skill when maintaining or running the local Douyin creator video and commerce tracker that connects to an existing Google Chrome CDP session, collects creator profile videos, extracts product_name and real product_id, and writes Excel outputs.
---

# Douyin Creator Tracker Skill

## When to use

Use this skill for tasks involving the local project:

```text
C:\cutting video\douyin_creator_tracker
```

Typical requests:

- Run a Douyin creator profile collection.
- Debug missing `product_id`.
- Add multi-creator or incremental collection.
- Validate an Excel output.
- Adjust humanized browser behavior.

## Rules

- Do not use Playwright to create a browser.
- Use Google Chrome Stable launched with CDP.
- Reuse the user's logged-in Chrome profile.
- Reuse one Douyin tab sequentially; do not open one tab per video.
- Up to 5 tabs is acceptable only when necessary, and extra Douyin tabs should be closed after collection.
- Do not click payment, follow, private message, or account-changing actions.
- Keep `outputs/` and `evidence/` local; do not commit them.

## Standard commands

Validate code:

```powershell
cd "C:\cutting video\douyin_creator_tracker"
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py
```

Run current creator all discoverable works:

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --out "outputs\douyin_creator_tracker_current_creator_all_discoverable.xlsx" --evidence-dir "evidence\douyin_creator_tracker_current_creator_all_discoverable" --retries 1
```

Run multiple creators incrementally:

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --close-extra-tabs --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 1
```

## Validation

After a run, read the Excel and report:

- rows
- unique videos
- status counts
- missing `product_id`
- duplicate video rows
- output path

## Known data sources

- Profile video list: `/aweme/v1/web/aweme/post/`, top-level `aweme_list`.
- Video detail and product anchor: `aweme/v1/web/aweme/detail`, `anchorInfo.extra`.
- Product detail fallback: `ecom/product/detail/saas/pc`.

## Important distinction

The page config `a11y-configs` may contain `product_id:100005`; this is accessibility SDK config, not commerce product ID.
