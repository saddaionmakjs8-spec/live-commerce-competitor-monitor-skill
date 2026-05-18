# Delivery Package Protocol

Use this after a valid monitoring run has produced raw evidence and structured event data. The goal is a folder the user can open directly, without seeing engineering artifacts first.

## Principle

Separate the output into two layers:

1. **User-facing delivery folder**: only files the user naturally wants to open.
2. **`_internal_技术底稿`**: raw JSONL, logs, source CSVs, validation notes, and other audit material.

Do not expose `raw/`, `report/`, `events.jsonl`, audio temp files, or English engineering filenames in the delivery folder root.

## Required Root Layout

```text
账号_直播分析_YYYY-MM-DD_时长/
├── 00_先看这个_本次结论.md
├── 01_完整录屏_账号_YYYY-MM-DD_时长.mov
├── 02_直播逐字稿_带时间轴.xlsx
├── 03_结构化数据总表.xlsx
├── 04_关键截图/
├── 05_话术分析报告.md
├── 06_截图索引图.jpg
└── _internal_技术底稿/
```

If a file is missing, keep the slot out or clearly state the missing evidence in `00_先看这个_本次结论.md`; do not create fake placeholders.

## File Naming Rules

- Use Chinese names for user-facing files and folders.
- Use the account name, date, and duration in the recording filename.
- Screenshots must use recording time plus visible meaning:
  - `02分40秒_切到5号能多益89元_热卖46_在线43.png`
  - `03分40秒_切到4号小金砖88.8元_品质问题.png`
- Avoid pinyin and code slugs in the delivery layer.
- Technical filenames can remain unchanged inside `_internal_技术底稿`.

## Workbook Requirements

`02_直播逐字稿_带时间轴.xlsx` should include:

- `逐字稿`: start time, end time, auto transcript, confidence hint, notes.
- `高价值话术提炼`: reviewed high-value sales lines grouped by type.

`03_结构化数据总表.xlsx` should include:

- `总览`
- `时间线`
- `话术库`
- `商品切换`
- `人数与热卖`
- `评论问题`
- `下单信号`
- `截图索引`
- `循环判断`

Use Chinese headers and keep columns readable. This workbook is the main reusable analysis asset.

## Internal Folder

Put audit material here:

- `events.jsonl`
- `采集说明.md`
- `原始报表csv/`
- `窗口录制范围验证.png`
- `音频有效性检查.txt`
- `逐字稿原始json.json`

Do not delete source evidence unless the user explicitly asks. The delivery package can copy or reference evidence, but the original run folder remains the technical source of truth.

## Script

After `build_live_report.py` has produced `report/`, run:

```bash
python .codex/skills/live-commerce-competitor-monitor/scripts/build_delivery_package.py \
  --run-dir output/live-monitor/YYYY-MM-DD-account-run
```

Optional:

```bash
python .codex/skills/live-commerce-competitor-monitor/scripts/build_delivery_package.py \
  --run-dir output/live-monitor/YYYY-MM-DD-account-run \
  --out-dir output/live-monitor/账号_直播分析_YYYY-MM-DD_10分钟 \
  --account-name 账号 \
  --date YYYY-MM-DD \
  --duration-label 10分钟
```

The script expects:

- `events.jsonl`
- `report/*.csv`
- `raw/screen-recording-*.mov`
- `raw/screenshots/`
- `raw/transcript_segments.csv` when transcript delivery is required

If `openpyxl` is missing, run the script with the bundled Codex Python runtime.
