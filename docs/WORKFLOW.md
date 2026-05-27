# Workflow

## 1. 环境准备

退出所有 Chrome 后启动同一 profile 的 CDP Chrome：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

检查 CDP：

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

## 2. 小样本验证

```powershell
cd "C:\cutting video\douyin_creator_tracker"
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --limit 3 --humanize --out "outputs\smoke3.xlsx" --evidence-dir "evidence\smoke3"
```

读回 Excel，确认有 `video_id`、`product_name`、`product_id`。

## 3. 全量可发现作品采集

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --out "outputs\douyin_creator_tracker_current_creator_all_discoverable.xlsx" --evidence-dir "evidence\douyin_creator_tracker_current_creator_all_discoverable" --retries 1
```

## 4. 数据清洗规则

- `product_id` 优先取响应里的真实 `product_id`。
- `promotion_id` 可作为商品卡线索，但不能覆盖真实 `product_id`。
- 点击商品卡补采时，商品名必须和视频标题中的孕妇裤、裙、孕妇装等关键词相关。
- 推荐商品污染要删除或标记为 `ok_no_product_after_cleaning`。

## 5. 结果验收

用 `openpyxl` 读回输出 Excel 并统计：

- 总行数
- 去重视频数
- 状态分布
- 缺商品 ID 数
- 重复视频行

## 6. 多达人流程

当前建议串行运行多个达人，不并发：

1. 复用同一个 CDP Chrome。
2. 每个达人一个输出 Excel。
3. 每个达人一个 evidence 子目录。
4. 一个达人结束并验收后，再跑下一个达人。
