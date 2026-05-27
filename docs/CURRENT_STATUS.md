# Current Status

更新时间：2026-05-28

## 已跑通达人

- 达人名：是小鹿吖
- 输入链接：`https://v.douyin.com/yrNAdFgturw/`
- 最终主页：`https://www.douyin.com/user/MS4wLjABAAAAyFZVSmhGi_0cmIO1LoMtITYrZEKQPMOOyBEac9JEyMo`
- 页面标记作品数：`91`

## 最终本地结果

```text
C:\cutting video\douyin_creator_tracker\outputs\douyin_creator_tracker_current_creator_all_discoverable.xlsx
```

统计：

- rows：`91`
- videos：`91`
- status：
  - `ok`: `84`
  - `ok_no_product_after_cleaning`: `7`
- missing_product_id：`7`
- duplicate_video_rows：`0`

## 已验证突破口

- 视频商品信息可从 `aweme/v1/web/aweme/detail` 的 `anchorInfo.extra` 获取。
- 真实商品 ID 是响应中的 `product_id`。
- `promotion_id` 不是最终要写入 `product_id` 字段的值。
- 作品列表来自 `/aweme/v1/web/aweme/post/` 顶层 `aweme_list`。
- 该达人 PC 作品列表分页最终返回 `has_more=0`。

## 仍可增强

- 多达人批量队列。
- 增量采集数据库，避免重复采历史视频。
- 更细的商品污染判定。
- 采集结果自动汇总报告。
