# AGENTS.md

## Goal

Maintain a reusable Douyin creator video and commerce tracking tool. Prioritize verifiable runs, checkpoint recovery, and low-risk browser behavior.

## Project Conventions

- Project root: `C:\cutting video\douyin_creator_tracker`
- Entry point: `douyin_creator_tracker.py`
- Web console: `web_app.py`
- Keep-awake helper: `keep_awake.py`
- Outputs: `outputs\`
- Evidence: `evidence\`
- Incremental index: `outputs\collected_index.json`
- Test command: `python test_parser.py`

## Operating Rules

- Do not create a browser with Playwright.
- Use Google Chrome Stable through CDP.
- Reuse the user's logged-in Chrome profile.
- Prefer one Douyin working tab and sequential collection.
- Keep tab count low; use `--close-extra-tabs --max-tabs 3` for long runs.
- Use `--humanize` for slow collection, with 3 to 9 second delays.
- Write Excel after every video.
- Update the incremental index after every video.
- Use `--profile-list` for multiple creators.
- Use `--incremental --incremental-db outputs\collected_index.json` for resume.
- For daily incremental runs, keep `--all --incremental` and use smart window defaults:
  - `--incremental-daily-max 10`
  - `--incremental-lookback-days 1`
- Smart window behavior:
  - Existing creator: check roughly `(days_since_last_collect + lookback_days) * daily_max`.
  - New creator in index: fallback to full scan automatically.
- Keep Windows awake during long runs unless the user asks otherwise.
- Keep failed videos as rows and continue the batch.

## Edit Rules

- Read the current README, workflow, and runbook before changing code.
- Keep changes narrow and tied to collection, parsing, export, or recovery.
- Do not commit `outputs\`, `evidence\`, browser cache, or account data.
- After edits, run:

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py keep_awake.py
```

## Known Risks

- Douyin page and API fields can change.
- `product_id` must come from real commerce responses; do not use `promotion_id` as final `product_id`.
- Product card clicks can expose unrelated recommendations, so relevance filtering is required.
- CDP can disconnect; reconnect and retry the current video when possible.
- Checkpoint resume exists, but there is no external watchdog runner yet.
- If `outputs\collected_index.json` is corrupted, smart incremental window and profile history matching may degrade to safer full scan behavior.
