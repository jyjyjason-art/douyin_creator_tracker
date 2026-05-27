# Douyin Creator Tracker

抖音达人视频发布与带货商品追踪工具。当前版本使用本机 Google Chrome Stable + CDP 复用已登录的 Chrome profile，按达人主页采集视频与商品信息并输出 Excel。

## 当前状态

已在达人 `是小鹿吖` 上完成端到端验证：

- 达人链接：`https://v.douyin.com/yrNAdFgturw/`
- PC 主页标记作品数：`91`
- 已采集可发现视频：`91`
- 有效带货商品行：`84`
- 清洗后判定无有效商品：`7`
- 重复视频行：`0`
- 最终本地结果：`outputs/douyin_creator_tracker_current_creator_all_discoverable.xlsx`

## 采集字段

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

## 核心原则

- 不用 Playwright 创建浏览器。
- 只连接已经启动的 Google Chrome CDP。
- 复用同一个已登录 Chrome profile。
- 默认复用一个已有 Douyin 标签页顺序采集，不为每个视频或达人新开标签。
- 慢速采集时使用 `3~9` 秒随机停顿，并在达人主页做一屏左右的无意义滚动。
- 每条视频采集后 checkpoint 写入 Excel，避免中断后结果丢失。

## 启动 Chrome CDP

先退出所有 Chrome，再用同一个用户数据目录和 profile 启动：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

如果 Chrome 在 x86 目录：

```powershell
& "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

## 常用命令

进入项目目录：

```powershell
cd "C:\cutting video\douyin_creator_tracker"
```

采集指定达人当前可发现全部作品：

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --out "outputs\douyin_creator_tracker_current_creator_all_discoverable.xlsx" --evidence-dir "evidence\douyin_creator_tracker_current_creator_all_discoverable" --retries 1
```

采集前 20 条：

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --limit 20 --humanize --out "outputs\douyin_creator_tracker_limit20.xlsx" --evidence-dir "evidence\douyin_creator_tracker_limit20"
```

多达人批量增量采集：

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --close-extra-tabs --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 1
```

`profiles.txt` 每行一个达人链接；空行和 `#` 开头的注释会跳过。增量索引默认写入 `outputs/collected_index.json`，已采集过的 `video_id` 会跳过。

清理多余 Douyin 标签：

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --limit 5 --close-extra-tabs --max-tabs 3
```

只采一个视频：

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --target-video-id 7644168958324866981 --out "outputs\douyin_target_7644168958324866981.xlsx" --evidence-dir "evidence\douyin_target_7644168958324866981"
```

解析 HAR：

```powershell
python douyin_creator_tracker.py --har "C:\path\to\douyin.har" --video-id 7644168958324866981 --out "outputs\douyin_har_product.xlsx"
```

## 验证

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py
```

## 关键发现

真实商品 ID 不在普通视频页 DOM 中。已验证的优先数据源：

- `aweme/v1/web/aweme/detail`：视频对象中的 `anchorInfo.extra` / `anchor_info.extra`。
- `ecom/product/detail/saas/pc`：商品详情响应。
- 达人作品列表来自 `/aweme/v1/web/aweme/post/` 的顶层 `aweme_list`，分页字段为 `max_cursor` / `has_more`。

页面里 `a11y-configs` 的 `product_id:100005` 是无障碍 SDK 配置，不是商品 ID。

## 文档

- [Agent](agents/douyin_creator_tracker_agent.md)
- [Workflow](docs/WORKFLOW.md)
- [Runbook](docs/RUNBOOK.md)
- [Current Status](docs/CURRENT_STATUS.md)
- [Skill](skills/douyin-creator-tracker/SKILL.md)
