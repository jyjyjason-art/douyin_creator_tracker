@echo off
setlocal
cd /d "C:\cutting video\douyin_creator_tracker"

echo [1/2] Resume: xiaotaoyun pregnancy creator
python douyin_creator_tracker.py ^
  --profile-url "https://www.douyin.com/user/MS4wLjABAAAAx8H4TS8yOdyuOavcZabgS1_biCj2MUNlb2Cfj8a1HC2ialQtio-kE4Jgge-bEBLr?from_tab_name=main" ^
  --all ^
  --humanize ^
  --incremental ^
  --incremental-db "outputs\collected_index.json" ^
  --out "C:\cutting video\douyin_creator_tracker\outputs\douyin_new_creator_20260602_191025.xlsx" ^
  --evidence-dir "C:\cutting video\douyin_creator_tracker\evidence\douyin_new_creator_20260602_191025" ^
  --retries 2 ^
  --close-extra-tabs ^
  --max-tabs 3

echo.
echo [2/2] Batch collect queued creators
python douyin_creator_tracker.py ^
  --profile-list "outputs\profiles_queue_20260603.txt" ^
  --all ^
  --humanize ^
  --incremental ^
  --incremental-db "outputs\collected_index.json" ^
  --out "C:\cutting video\douyin_creator_tracker\outputs\douyin_batch_20260603_queue.xlsx" ^
  --evidence-dir "C:\cutting video\douyin_creator_tracker\evidence\douyin_batch_20260603_queue" ^
  --retries 2 ^
  --close-extra-tabs ^
  --max-tabs 3

echo.
echo Queue finished. Press any key to close.
pause >nul
