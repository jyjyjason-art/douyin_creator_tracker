# AGENTS.md

## 目标

维护一个可复用的抖音达人视频发布与带货商品追踪工具。优先保证可验证、可恢复、低风控风险，不追求一次性大而全。

## 当前项目约定

- 项目根目录：`C:\cutting video\douyin_creator_tracker`
- 脚本入口：`douyin_creator_tracker.py`
- 运行结果：`outputs/`
- 日志证据：`evidence/`
- 测试入口：`python test_parser.py`

## 执行原则

- 不使用 Playwright 创建浏览器。
- 使用 Google Chrome Stable + CDP。
- 复用用户已登录的 Chrome profile。
- 默认单标签顺序采集，不为每个视频新开标签。
- 多达人采集时也复用同一个 Chrome 和一个工作标签，按达人链接排队。
- 必要时可以临时打开标签，但总数控制在 5 个以内，并在采集后关闭多余 Douyin 标签。
- 慢速采集默认启用 `--humanize`，随机停顿 `3~9` 秒。
- 每条视频采集后立即 checkpoint 写 Excel。
- 多达人批量使用 `--profile-list`；增量跳过使用 `--incremental`。
- 失败视频保留一行，不中断整个任务。

## 修改规则

- 先读现有入口和 README，再改代码。
- 只做与采集、解析、导出相关的最小改动。
- 不把 `outputs/`、`evidence/`、浏览器缓存、账号数据提交到 Git。
- 修改后必须跑：

```powershell
python test_parser.py
python -m py_compile douyin_creator_tracker.py test_parser.py
```

## 已知风险

- 抖音页面和接口会变化，字段名可能漂移。
- 当前商品 ID 以响应中的真实 `product_id` 优先，`promotion_id` 不应误写到 `product_id` 字段。
- 点击商品卡后可能出现推荐商品污染，必须做视频标题相关性清洗。
- CDP 偶发断线时需要重连并重试当前视频。
