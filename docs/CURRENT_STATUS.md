# Current Status

Updated: 2026-05-28

## Implemented and Verified

- Google Chrome Stable + CDP control.
- Reuse of the user's logged-in Chrome profile.
- Short-link resolution.
- Creator profile video scanning.
- Single-creator and multi-creator inputs.
- Incremental collection and checkpoint resume.
- Excel checkpoint after every video.
- Windows keep-awake.
- CDP stale target skip and reconnect retry.
- Extra tab control.

## Verified Runs

### Early smoke creator

- Source short link: `https://v.douyin.com/yrNAdFgturw/`
- Page work count: `91`
- Collected unique videos: `91`
- Local output: `outputs\douyin_creator_tracker_current_creator_all_discoverable.xlsx`

### Creator profile ending in `...G36`

- Profile URL contains: `MS4wLjABAAAAiGmBlS9r1qi0r8PeGew2kv2vVPUUgfk3u-GQrlOAU25w5kVLKihX3DLH3-nU0G36`
- Page work count: `794`
- Incremental index unique videos: `794`
- Results are split across:
  - `outputs\douyin_two_new_creators_20260528_030419.xlsx`
  - `outputs\douyin_two_new_creators_resume_20260528_121054.xlsx`
  - `outputs\douyin_two_new_creators_resume_20260528_133945.xlsx`

## Latest Batch State

Two-creator batch file:

- Profile list: `evidence\profile_list_two_creators_20260528.txt`
- Output: `outputs\douyin_two_new_creators_resume_20260528_133945.xlsx`
- Evidence: `evidence\douyin_two_new_creators_resume_20260528_133945`

Second creator only follow-up:

- Profile list: `evidence\profile_list_second_creator_20260528.txt`
- Output: `outputs\douyin_second_creator_resume_20260528_165218.xlsx`
- Evidence: `evidence\douyin_second_creator_resume_20260528_165218`
- Collection was manually stopped at the user's request.
- Saved rows: `209`
- Unique videos in this output: `208`
- Status counts: `ok=125`, `partial_product_not_exposed=83`, `ok_no_product_detected=1`
- Missing product ID rows: `84`
- Incremental index count for the second creator: `294`

This is runtime state only. Runtime outputs are not committed to GitHub.

## Completed Creator: `MS4wLjABAAAA-172...`

- Profile URL contains: `MS4wLjABAAAA-172HQ5SFcyboQgcS_BPlb-5QlvEEgVZQbEuWRp3FUBVFIO3GTq4a3iyB7qi17-x`
- Creator name in output: `Yiyi (Chinese name in Excel)`
- Output: `outputs\douyin_new_creator_20260528_191029.xlsx`
- Evidence: `evidence\douyin_new_creator_20260528_191029`
- Rows: `260`
- Unique videos: `185`
- Status counts: `ok=255`, `partial_product_not_exposed=3`, `ok_no_product_detected=2`
- Missing product ID rows: `5`

## Completed Creator: `MS4wLjABAAAAj_5...`

- Profile URL contains: `MS4wLjABAAAAj_5VWyinmz-TmBcVPuibD377cwP7-kNqfDaTmPpu_GA0qsxNBloiRSHYM_wA1oeF`
- Creator name in output: `Hanhan maternity outfits (Chinese name in Excel)`
- Output: `outputs\douyin_creator_j5v_20260529_155939.xlsx`
- Evidence: `evidence\douyin_creator_j5v_20260529_155939`
- Rows: `1928`
- Unique videos: `1925`
- Duplicate video rows: `3`
- Status counts: `ok=1669`, `partial_product_not_exposed=168`, `ok_no_product_detected=91`
- Rows with product ID: `1669`
- Missing product ID rows: `259`

## Product ID Findings

- Product data can be extracted from `/aweme/v1/web/aweme/detail` and `anchorInfo.extra`.
- Real product ID is response field `product_id`.
- `promotion_id` is not the final value for `product_id`.
- Profile works come from `/aweme/v1/web/aweme/post/` top-level `aweme_list`.
- `a11y-configs product_id:100005` is not a commerce product ID.

## Next Useful Improvements

- External runner/watchdog to restart the Python process automatically.
- Utility to merge checkpoint Excel files into one creator-level output.
- Better separation of "no product" vs "product API did not expose data".
- More regression samples for product recommendation pollution.
