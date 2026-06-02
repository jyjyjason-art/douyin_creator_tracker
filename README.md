# Douyin Creator Tracker

Local Douyin creator video and commerce tracker.

The tracker uses Google Chrome Stable through CDP and reuses the user's logged-in Chrome profile. It does not create a browser with Playwright.

## Paths

- Project root: `C:\cutting video\douyin_creator_tracker`
- Main script: `douyin_creator_tracker.py`
- Web console: `web_app.py`
- Keep-awake helper: `keep_awake.py`
- Results: `outputs\`
- Logs, screenshots, evidence: `evidence\`
- Incremental index: `outputs\collected_index.json`
- Master creator list: `outputs\profiles_master.txt`

`outputs\` and `evidence\` are local runtime artifacts and are intentionally ignored by Git.
Exception: `outputs\collected_index.json` is intentionally tracked to preserve incremental history across environments.

## Current Capabilities

- Connect to an existing Chrome CDP endpoint.
- Reuse the user's existing Chrome profile and login state.
- Accept Douyin short links and long creator profile URLs.
- Collect one creator, multiple creators, or one target video.
- Collect all currently discoverable works with `--all`.
- Parse HAR files offline with `--har`.
- Use humanized delays and idle scrolls with `--humanize`.
- Resume by `video_id` with `--incremental`.
- Smart incremental window for daily runs:
  - Existing creators: auto-check a bounded top window instead of scanning all videos.
  - New creators: automatic full scan fallback.
- Write Excel checkpoints after every video.
- Update `outputs\collected_index.json` after every video.
- Limit extra Douyin tabs with `--close-extra-tabs --max-tabs 3`.
- Keep Windows awake during long runs by default.
- Recover from some CDP stale target and reconnect failures.

Important limitation: checkpoint resume works, but there is no external watchdog runner yet. If the Python process exits completely, restart the same incremental command to continue.

## Output Fields

- `creator_name`
- `creator_profile_url`
- `source_profile_url`
- `video_id`
- `video_url`
- `video_title`
- `publish_time`
- `has_product`
- `product_name`
- `product_id`
- `product_url`
- `collect_time`
- `collect_status`
- `error_message`

## Incremental Index File

- File: `outputs\collected_index.json`
- Role:
  - stores per-profile collected `video_id`s and per-video collection metadata
  - drives resume and dedupe behavior for `--incremental`
- provides last-collect timestamps for smart incremental window estimation

## Master Creator List

- File: `outputs\profiles_master.txt`
- Role:
  - canonical list of all collected creator profile URLs
  - recommended input for global incremental update runs
  - deduped from collected history and maintained as a stable batch source

## Status Values

- `ok`: collection finished normally.
- `ok_no_product_detected`: no product was detected.
- `partial_product_not_exposed`: the video looks commercial, but no valid product ID was exposed.
- `partial_login_required_for_product`: login or permission state likely blocked product detail.
- `failed`: one video failed; the batch should continue.

## Start Chrome CDP

Close all Chrome windows first, then start Chrome with the same user data directory:

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

If Chrome is installed under Program Files (x86):

```powershell
& "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

Check CDP:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

## Common Commands

Enter the project:

```powershell
cd "C:\cutting video\douyin_creator_tracker"
```

Collect one creator:

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --out "outputs\douyin_creator.xlsx" --evidence-dir "evidence\douyin_creator" --retries 2 --close-extra-tabs --max-tabs 3
```

Collect multiple creators:

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 2 --close-extra-tabs --max-tabs 3
```

Daily incremental with smart window (recommended):

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --incremental-daily-max 10 --incremental-lookback-days 1 --out "outputs\douyin_daily.xlsx" --evidence-dir "evidence\douyin_daily" --retries 2 --close-extra-tabs --max-tabs 3
```

Disable smart window and force full scan while still skipping collected IDs:

```powershell
python douyin_creator_tracker.py --profile-url "https://www.douyin.com/user/xxx" --all --incremental --disable-smart-incremental-window --incremental-db "outputs\collected_index.json"
```

`profiles.txt` should contain one creator URL per line. Blank lines and lines starting with `#` are skipped.

Collect one target video:

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --target-video-id 7644168958324866981 --out "outputs\douyin_target.xlsx" --evidence-dir "evidence\douyin_target" --retries 2
```

Parse HAR:

```powershell
python douyin_creator_tracker.py --har "C:\path\to\douyin.har" --video-id 7644168958324866981 --out "outputs\douyin_har_product.xlsx"
```

Start web console:

```powershell
python web_app.py
```

Open `http://127.0.0.1:5088`.

## Smart Incremental Window

- Active when:
  - `--incremental` is enabled
  - `--all` is enabled
  - `--disable-smart-incremental-window` is not set
- Formula:
  - `window = (days_since_last_collect + incremental_lookback_days) * incremental_daily_max`
- Defaults:
  - `incremental_daily_max=10`
  - `incremental_lookback_days=1`
- New creator handling:
  - If the creator has no history in `outputs\collected_index.json`, the tracker falls back to full scan.

## Validation

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py keep_awake.py
```

## Verified Results

First large creator run:

- Creator profile contains `MS4wLjABAAAAiGmBlS9r1qi0r8PeGew2kv2vVPUUgfk3u-GQrlOAU25w5kVLKihX3DLH3-nU0G36`
- Page work count: `794`
- Incremental index unique videos: `794`
- Results are split across checkpoint Excel files under `outputs\`

Earlier smoke creator:

- Source short link: `https://v.douyin.com/yrNAdFgturw/`
- Page work count: `91`
- Collected unique videos: `91`

## Product ID Findings

Real commerce product IDs are not reliably present in normal DOM text. Preferred sources:

- `/aweme/v1/web/aweme/detail`, especially `anchorInfo.extra` and `anchor_info.extra`
- `/ecom/product/detail/saas/pc`
- `/aweme/v1/web/aweme/post/`, top-level `aweme_list`

The page config value `a11y-configs product_id:100005` is accessibility SDK config, not a commerce product ID.

## Docs

- [Agent](agents/douyin_creator_tracker_agent.md)
- [Workflow](docs/WORKFLOW.md)
- [Runbook](docs/RUNBOOK.md)
- [Current Status](docs/CURRENT_STATUS.md)
- [Skill](skills/douyin-creator-tracker/SKILL.md)
