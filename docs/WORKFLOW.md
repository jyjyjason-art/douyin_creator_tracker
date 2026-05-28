# Workflow

## 1. Prepare Chrome

Close all Chrome windows, then start Chrome with CDP and the same user profile:

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

Check CDP:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

Enter the project:

```powershell
cd "C:\cutting video\douyin_creator_tracker"
```

## 2. Smoke Test

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --limit 3 --humanize --out "outputs\smoke3.xlsx" --evidence-dir "evidence\smoke3" --retries 2
```

Read the Excel file and verify `video_id`, `video_title`, and `collect_status`. For commerce videos, check `product_name` and real `product_id`.

## 3. Single Creator Full Collection

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --out "outputs\douyin_creator.xlsx" --evidence-dir "evidence\douyin_creator" --retries 2 --close-extra-tabs --max-tabs 3
```

Flow:

1. Connect to Chrome CDP.
2. Open the short or long creator URL.
3. Resolve the final creator profile URL.
4. Scan creator works from DOM and `/aweme/v1/web/aweme/post/`.
5. Skip indexed `video_id`s when `--incremental` is enabled.
6. Open each video page.
7. Extract title, publish time, product name, and real `product_id`.
8. Write Excel and incremental index after each video.

## 4. Multiple Creator Batch

Create `profiles.txt`:

```text
https://www.douyin.com/user/xxx
https://www.douyin.com/user/yyy
```

Run:

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 2 --close-extra-tabs --max-tabs 3
```

The current strategy is serial collection, not parallel creator collection.

## 5. Resume

Resume depends on:

- Excel checkpoint after every video.
- Incremental index update after every video.

If network, CDP, or system issues stop the Python process, rerun the same command with `--incremental`. The tracker scans the profile again and skips already collected `video_id`s.

This is not a full watchdog mode. A separate runner is still needed for automatic restart after process exit.

## 6. Cleaning Rules

- Prefer real `product_id` from commerce responses.
- Use `promotion_id` only as a clue, not as final `product_id`.
- Product names collected from product cards must be relevant to the video title or text.
- Recommendation pollution should be removed or marked as not exposing a valid product.

## 7. Acceptance

Use `openpyxl` to read the output and report:

- total rows
- unique videos
- `collect_status` distribution
- rows missing `product_id`
- duplicate video rows
- output path

Code validation:

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py keep_awake.py
```
