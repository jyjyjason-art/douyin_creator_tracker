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

Last observed local state while updating docs:

- No `douyin_creator_tracker.py` process was running.
- Output had `77` rows.
- First large creator was complete in the incremental index.
- Second creator had begun and had at least `39` rows in the latest output.

This is runtime state only. Runtime outputs are not committed to GitHub.

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
