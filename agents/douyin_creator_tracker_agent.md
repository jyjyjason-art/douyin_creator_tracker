# Douyin Creator Tracker Agent

## Role

Maintain and run the local Douyin creator video and commerce tracking workflow.

## Inputs

- Creator short link or long profile URL.
- One target video ID.
- A profile list file.
- Collection mode: limit, target video, or all discoverable works.
- Incremental strategy:
  - Smart daily window for existing creators.
  - Full scan fallback for new creators.
- Output Excel path and evidence directory.

## Output Contract

Excel fields:

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

## Boundaries

- Do not create a Playwright browser.
- Do not switch or create Chrome profiles.
- Do not open one tab per video.
- Do not click payment, order, follow, or private-message actions.
- Do not commit `outputs\` or `evidence\`.

## Standard Flow

1. Verify CDP at `http://127.0.0.1:9222/json/version`.
2. Open or reuse the creator profile tab.
3. Resolve final creator profile URL.
4. Collect videos from DOM and `/aweme/v1/web/aweme/post/`.
5. If `--all --incremental`, use smart window:
   - existing creator: `(days_since_last_collect + lookback_days) * daily_max`
   - new creator: full scan fallback
6. Skip existing `video_id`s when incremental mode is enabled.
7. Open each video page.
8. Extract title, publish time, product name, and real `product_id` from network responses first.
9. Click product card only as fallback, then filter by title relevance.
10. Write Excel and incremental index after every video.
11. Read the Excel and report acceptance statistics.

## Recovery Strategy

- Keep a row for failed videos.
- Retry CDP disconnects when possible.
- Rerun the same `--incremental` command after process exit.
- Do not delete old Excel files; they are checkpoints and evidence.

## Acceptance

Do not rely only on exit code. Read Excel and report:

- rows
- unique videos
- `collect_status` distribution
- missing `product_id` rows
- duplicate video rows
- output path
