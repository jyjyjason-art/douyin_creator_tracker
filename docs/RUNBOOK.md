# Runbook

## Commands

Enter project:

```powershell
cd "C:\cutting video\douyin_creator_tracker"
```

Start Chrome CDP:

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9223 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

Single creator:

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --incremental-daily-max 10 --incremental-lookback-days 1 --out "outputs\douyin_creator.xlsx" --evidence-dir "evidence\douyin_creator" --retries 2 --close-extra-tabs --max-tabs 3
```

Multiple creators:

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --incremental-db "outputs\collected_index.json" --incremental-daily-max 10 --incremental-lookback-days 1 --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 2 --close-extra-tabs --max-tabs 3
```

Force full scan for an existing creator:

```powershell
python douyin_creator_tracker.py --profile-url "https://www.douyin.com/user/xxx" --all --incremental --disable-smart-incremental-window --incremental-db "outputs\collected_index.json"
```

Web console:

```powershell
python web_app.py
```

## Check Runtime Status

Python processes:

```powershell
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object { $_.CommandLine -like '*douyin_creator_tracker.py*' -or $_.CommandLine -like '*keep_awake.py*' } | Select-Object ProcessId,CommandLine | Format-List
```

Run log:

```powershell
Get-Content "evidence\douyin_batch\run.log" -Tail 80
```

stderr:

```powershell
Get-Content "evidence\douyin_batch.stderr.log" -Tail 80
```

## Troubleshooting

### Sleep or Standby

The tracker calls Windows `SetThreadExecutionState` by default. For older already-running tasks, start:

```powershell
python keep_awake.py
```

`evidence\keep_awake.log` should keep receiving `SetThreadExecutionState active`.

### CDP Is Not Reachable

Symptoms:

- `Cannot connect to Chrome CDP`
- `http://127.0.0.1:9223/json/version` fails

Fix:

1. Close all Chrome windows.
2. Restart Chrome with `--remote-debugging-port=9223`.
3. Rerun the collection command with `--incremental`.

### CDP Disconnect or Stale Target

Symptoms:

- `CDP receive loop stopped unexpectedly`
- `CDP timeout: Page.enable`
- `CDP timeout: Page.navigate`
- `CDP timeout: Page.captureScreenshot`

Current behavior:

- Close old CDP page.
- Skip stale targets.
- Create a fresh target.
- Retry the current video.

If the process exits anyway, rerun the same incremental command.

### Too Many Tabs

Use:

```powershell
--close-extra-tabs --max-tabs 3
```

Old tabs can also be closed manually or by restarting Chrome.

### Smart Incremental Window Behavior

When `--all --incremental` is used, and smart window is enabled:

- Existing creator: window size is `(days_since_last_collect + incremental_lookback_days) * incremental_daily_max`.
- New creator in index: automatic full scan.
- To disable smart window: add `--disable-smart-incremental-window`.

### Empty Product ID

Possible causes:

- The video has no product.
- The product card was not exposed.
- Douyin fields changed.
- A recommendation product was filtered out as unrelated.

Actions:

1. Check `collect_status`.
2. Check `error_message`.
3. Re-run the video with `--target-video-id`.
4. Save HAR and parse it with `--har` when needed.

## Validation

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py keep_awake.py
```
