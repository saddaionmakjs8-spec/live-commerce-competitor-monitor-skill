# 输入输出约定

## 支持的输入目录

### 中文交付目录

优先支持这种目录：

```text
账号_直播分析_YYYY-MM-DD_时长/
├── 00_先看这个_本次结论.md
├── 01_完整录屏_*.mov
├── 02_直播逐字稿_带时间轴.xlsx
├── 03_结构化数据总表.xlsx
├── 04_关键截图/
├── 05_话术分析报告.md
└── _internal_技术底稿/
    └── 原始报表csv/
```

### 技术底稿目录

如果用户给的是技术运行目录，脚本会尝试识别：

```text
run-dir/
├── raw/
│   └── screenshots/
├── report/
│   ├── metric_samples.csv
│   ├── speech_segments.csv
│   ├── product_events.csv
│   ├── comment_events.csv
│   ├── order_signals.csv
│   └── summary.md
└── events.jsonl
```

## 识别的 CSV

- `session_meta.csv`: 平台、账号、采集方式、停止原因。
- `recording_chunks.csv`: 录屏文件、时长、音频有效性、录制范围。
- `metric_samples.csv`: 在线人数、热卖数、商品卡、价格。
- `speech_segments.csv`: 话术时间段、话术类型、原话、销售意图。
- `product_events.csv`: 商品切换、链接编号、价格、权益。
- `comment_events.csv`: 评论、问题、是否被回应。
- `order_signals.csv`: 热卖数变化、成交弹窗、库存变化等可观察信号。
- `screenshot_events.csv`: 截图时间、原因、画面状态。
- `loop_markers.csv`: 循环直播判断证据。

缺某个文件时，页面要降级显示，不中断生成。

## 数据模式

`auto` 模式同时判断结构化 JSON 数据大小和本地证据文件体积：

- JSON 数据小于等于阈值，且录屏/截图/工作簿等证据文件也小：内嵌结构化数据进 HTML。
- JSON 数据大于阈值，或本地证据文件较大：输出本地 JS 数据文件，由 HTML 调用。

视频和截图始终用相对路径引用，不转成 base64。原因是即使截图不多，录屏通常很大，转成 base64 会让 HTML 难以打开、难以发送、难以维护。

## 输出文件

默认 HTML：

```text
07_直播分析可视化看板.html
```

本地数据文件：

```text
_internal_技术底稿/html_data/直播分析数据.js
```

预览截图如果需要由执行者另行生成，不作为脚本默认输出。

## 页面必须包含

- 顶部结论区。
- KPI 卡片：在线开始、在线峰值、在线结束、热卖增量、话术片段、关键截图。
- 录屏播放器和文件入口。
- 在线人数与热卖变化图。
- 合并时间线。
- 高价值话术模块。
- 话术与数据关系。
- 可以借鉴与不要照搬。
- 关键截图索引。
- 结构化明细表。
