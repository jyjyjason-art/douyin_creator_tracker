# Runbook

## 常用命令

进入项目：

```powershell
cd "C:\cutting video\douyin_creator_tracker"
```

启动 Chrome CDP：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" --profile-directory="Default"
```

采集当前达人全部可发现作品：

```powershell
python douyin_creator_tracker.py --profile-url "https://v.douyin.com/yrNAdFgturw/" --all --humanize --out "outputs\douyin_creator_tracker_current_creator_all_discoverable.xlsx" --evidence-dir "evidence\douyin_creator_tracker_current_creator_all_discoverable" --retries 1
```

多达人增量批量采集：

```powershell
python douyin_creator_tracker.py --profile-list "profiles.txt" --all --humanize --incremental --close-extra-tabs --out "outputs\douyin_batch.xlsx" --evidence-dir "evidence\douyin_batch" --retries 1
```

## 故障处理

### 电脑进入睡眠或待机

当前采集器默认会调用 Windows `SetThreadExecutionState` 防止系统睡眠和关闭显示。若正在运行的是旧版本任务，可单独启动保活进程：

```powershell
cd "C:\cutting video\douyin_creator_tracker"
python keep_awake.py
```

看到 `evidence\keep_awake.log` 持续写入 `SetThreadExecutionState active` 即表示保活生效。

### CDP 连接失败

现象：

- `Cannot connect to Chrome CDP`
- `http://127.0.0.1:9222/json/version` 不通

处理：

1. 退出所有 Chrome。
2. 重新用 `--remote-debugging-port=9222` 启动。
3. 再运行采集器。

### CDP 502 或标签页混乱

处理：

1. 保存当前 Excel。
2. 退出所有 Chrome。
3. 重新启动 CDP Chrome。
4. 重新运行，脚本会 checkpoint，不会影响已有最终文件。

### 出现很多标签

历史原因是旧版本每次连接 CDP 都新建标签。当前版本已修复为优先复用现有 Douyin 标签。旧标签可手动关闭或重启 Chrome 清理。

运行时可加：

```powershell
--close-extra-tabs --max-tabs 3
```

### 商品 ID 为空

可能原因：

- 该视频无带货商品。
- 商品卡被隐藏。
- 点击补采抓到的是推荐商品，被相关性清洗删除。
- 抖音接口字段变更。

处理：

1. 查看 `collect_status`。
2. 查看 `error_message`。
3. 对单条视频运行 `--target-video-id` 复核。

### 推荐商品污染

现象：视频讲孕妇裤，但商品名出现袜子、凉席、猫砂等。

处理：

- 保持标题相关性过滤开启。
- 若仍污染，增强 `product_matches_video_text` 的关键词规则。

## 验证命令

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py
```
