---
name: 直播竞品盯播分析
description: Long-duration live-commerce competitor monitoring, analysis, and delivery visualization. Use when the user wants to watch a competitor livestream, especially Douyin/TikTok Shop or Chinese e-commerce live rooms, and produce a user-friendly Chinese delivery folder with recording, transcript, screenshots, structured data, sales speech, viewer count, engagement, comments, product-card changes, order signals, conversion hypotheses, or a local HTML dashboard for the live-monitor results.
---

# 直播竞品盯播分析

## Purpose

Use this skill to turn a competitor livestream into reusable structured data, not a loose recap. The core question is:

```text
What sales speech and live-room actions appear before, during, or after changes in viewer count, engagement, comments, product focus, and observable order signals?
```

For long monitoring, prefer the local Douyin app or mobile mirror over browser pages. Browser live rooms are acceptable only for short probes or when app access is unavailable.

## First Decision

1. Confirm the platform, account, target live room, and intended monitoring duration.
2. Run every real monitoring task for at least 10 minutes. A shorter run is only a technical pilot, not a competitor analysis.
3. Use complete app-window recording from the start of monitoring until the stop condition is met. Screenshots are evidence bookmarks, not a replacement for recording.
4. If the task is longer than 10 minutes, use `references/local-douyin-capture.md`.
5. If the user asks for a one-off browser check, still collect data using the same schema in `references/data-schema.md`.
6. Before any real run, do a 30-60 second pilot and verify that the captured video shows only the target app/window area, comments, metrics, product cards, and audio are actually captured.
7. If complete spoken speech matters, do not start a formal run until audio capture and transcription are verified. Visible text is not a substitute for a transcript.

## Capture Stack

Use this priority order:

1. Local Douyin app, fixed-size window, app-window or fixed-region recording, event-driven screenshots from the same region, and audio transcription.
2. Mobile Douyin mirrored to Mac, then recorded from the mirrored window.
3. Browser live room, only when app capture is unavailable or the user explicitly requests browser.
4. Manual observation only as a fallback; mark missing fields and preserve screenshots.

Do not claim complete speech coverage unless audio was recorded and transcribed. If only visible text was available, label speech as `visible_text_only`.
Do not claim a formal capture if the recording or screenshots include unrelated desktop/app content outside the target Douyin window, unless that was explicitly approved and documented.

## Data Model

Record the live room as timestamped events. Keep raw evidence and cleaned event logs separate.

Minimum files for each run:

```text
output/live-monitor/YYYY-MM-DD-account/
├── raw/
│   ├── screen-recording-001.mov
│   ├── screenshots/
│   ├── audio-source-check.txt
│   ├── transcript_raw.txt
│   └── transcript_segments.csv
├── events.jsonl
├── report/
│   ├── recording_chunks.csv
│   ├── screenshot_events.csv
│   ├── loop_markers.csv
│   ├── metric_samples.csv
│   ├── speech_segments.csv
│   ├── product_events.csv
│   ├── comment_events.csv
│   ├── order_signals.csv
│   └── summary.md
└── assumptions.md
```

Use `references/data-schema.md` for required fields and category values.
Use `references/delivery-package.md` for the final user-facing folder. The delivery folder is mandatory for real runs; raw/report folders are technical source material, not the primary user deliverable.

## Recording And Stop Rules

- Record the full live room window/region continuously from task start to task stop. If files are split, log each chunk as a `recording_chunk`.
- The target must be the live-room software view, not the whole operator desktop. A full-display recording is a technical fallback only and must be marked as not window-scoped.
- Never stop before 10 minutes of valid recording, even if the room appears to loop earlier.
- If the stream is a looped recording, stop only after both conditions are true:
  - at least 10 minutes have been recorded
  - one complete content loop has been observed and marked with `loop_marker` events
- Treat a loop as complete only when the same visual/speech/product sequence returns to the starting marker with enough evidence. Use repeated opening frames, repeated product order, repeated on-screen copy, repeated speech, or repeated transition timing.
- If loop confidence is uncertain, continue recording or mark `stop_reason=manual_or_uncertain_loop`, not `loop_completed`.

## Sampling Rules

- Metrics: sample every 15-30 seconds during normal periods; every 5-10 seconds around spikes, product switches, coupon drops, or obvious order bursts.
- Speech: segment by selling intent, not by sentence. A segment usually lasts 5-45 seconds.
- Products: log every product-card change, price change, coupon mention, stock/limited-time claim, and cart/link number.
- Comments: log representative comments and all buyer-intent questions. Do not dump every low-value greeting unless volume itself matters.
- Order signals: log only observable signals, such as order popups, sold-count changes, hot-sale count changes, stock depletion, "xx just bought" notices, or product-card sales rank changes. Do not infer exact orders from crowd movement alone.
- Screenshots: take a screenshot when the visible state changes materially. Examples: product card appears/disappears, product/link changes, price/coupon changes, host switches product, camera angle/layout changes, order popup appears, comment burst starts, loop start/end marker appears, or an unusual claim is made on screen.
- Name screenshots by recording time and visible content, for example `00-12-34_product-card-1hao-1299.png` or `00-18-05_loop-start-gold-box-closeup.png`. Also log a matching `screenshot_event`.
- Screenshots must come from the same app-window or fixed-region capture area as the video. Do not save whole-desktop screenshots as live-room evidence.

## Formal Run Acceptance Gate

A run is not a formal competitor-analysis sample unless all required checks pass:

- `screen_scope=target_window_or_region`: the video and screenshots show the Douyin live room, not the operator's whole screen.
- `recording_valid=true`: the video is playable, non-black, and duration is at least the requested minimum.
- `audio_valid=true` when spoken speech or a transcript is required.
- `transcript_valid=true` when the deliverable includes a word-for-word transcript.
- `screenshots_valid=true`: screenshot filenames use recording timecode plus visible content and are taken only on material visual changes.
- `evidence_delivered=true`: the final response links the recording, transcript, screenshots folder, events JSONL, and report folder.

If any gate fails, mark the run as `technical_failure` or `pilot_only` and explain the missing piece before doing business analysis.

## Speech Classification

Classify each speech segment into one primary type:

- `product_intro`: ingredients, specs, flavor, quantity, usage scenario.
- `price_coupon`: price, coupon, discount, bundle, shipping, gift.
- `urgency`: limited time, limited stock, deadline, last chance.
- `trust`: official store, authenticity, after-sales, platform guarantee.
- `social_proof`: sold count, repeat buyers, popularity, ranking.
- `objection_handling`: answers about price, flavor, quality, shipping, gifting, expiry.
- `cta`: click link, place order, grab coupon, add cart, follow, join fan group.
- `interaction`: greeting, naming users, reading comments, asking questions.
- `scene_emotion`: gifting, holiday, romance, family, workplace, self-reward.
- `brand_story`: brand history, origin, craftsmanship, positioning.
- `operation`: anchor/store operations, product switch, technical notes.

For each segment, store the original quote when available. If the quote is approximate, set `quote_confidence=approximate`.

## Analysis Method

Analyze relationships by time window, not intuition.

1. Build a timeline of metric samples, speech segments, product events, comments, and order signals.
2. For each speech segment, compare metrics before and after:
   - default pre-window: 60 seconds before segment start
   - default post-window: 120 seconds after segment end
3. Calculate or describe:
   - online viewer delta
   - cumulative viewer or room-traffic delta if visible
   - likes delta
   - comment count and buyer-question count
   - order-signal count
   - product focus and price/coupon context
4. Mark causal confidence:
   - `strong`: repeated pattern across multiple similar segments and nearby order/engagement signals.
   - `medium`: one clear event with plausible timing.
   - `weak`: visible correlation but many confounders.
   - `unknown`: insufficient data.

Never overclaim. Write "the data suggests" when only correlation is available.

## Output

For every real run, produce two layers:

1. Technical source folder: raw recordings, raw screenshots, events JSONL, report CSVs, transcripts, assumptions.
2. User-facing delivery folder: Chinese filenames and only files the user naturally wants to open.

The delivery folder root must follow this shape:

```text
账号_直播分析_YYYY-MM-DD_时长/
├── 00_先看这个_本次结论.md
├── 01_完整录屏_账号_YYYY-MM-DD_时长.mov
├── 02_直播逐字稿_带时间轴.xlsx
├── 03_结构化数据总表.xlsx
├── 04_关键截图/
├── 05_话术分析报告.md
├── 06_截图索引图.jpg
├── 07_直播分析可视化看板.html
└── _internal_技术底稿/
```

Root-level files must use Chinese names. Do not put `events.jsonl`, `raw/`, logs, audio temp files, or English engineering filenames in the delivery root. Put those under `_internal_技术底稿`.

The final answer should link the delivery folder first and summarize:

1. `数据口径`: platform, account, duration, capture method, sample interval, missing fields.
2. `录制与截图证据`: recording chunks, screenshot count, naming quality, and any missing evidence.
3. `循环判断`: whether the live room is live, replay-like, or looped; stop reason and loop evidence.
4. `核心发现`: the 3-7 most important speech/action patterns.
5. `时间线`: major product switches, price/coupon events, viewer changes, order-signal bursts.
6. `话术库`: high-frequency and high-impact speech templates, grouped by type.
7. `关系分析`: which speech types appear closest to viewer growth, comment bursts, and order signals.
8. `竞品打法判断`: their live-room operating model, not just individual phrases.
9. `我们可以借鉴/不要照搬`: specific reusable tactics and risks.
10. `可视化看板`: if an HTML dashboard was requested or useful, link `07_直播分析可视化看板.html`.

When the user asks for data files, provide the user-facing Excel files first. Provide CSV/JSONL only if they explicitly ask for technical source data.

## Report Script

After collecting `events.jsonl`, run:

```bash
python .codex/skills/直播竞品盯播分析/scripts/build_live_report.py \
  --events output/live-monitor/YYYY-MM-DD-account/events.jsonl \
  --out-dir output/live-monitor/YYYY-MM-DD-account/report
```

The script expects JSONL records following `references/data-schema.md`. It outputs CSV tables and a first-pass summary. Review the summary manually before giving business conclusions.

Then build the delivery package:

```bash
python .codex/skills/直播竞品盯播分析/scripts/build_delivery_package.py \
  --run-dir output/live-monitor/YYYY-MM-DD-account
```

The delivery script creates the Chinese user-facing folder, copies/renames evidence, generates the transcript workbook and structured-data workbook, writes Markdown summaries, and moves technical artifacts into `_internal_技术底稿`.

## HTML Dashboard Script

When the user asks to present the monitoring result as HTML, or when the delivery should be more readable than Markdown/Excel alone, run:

```bash
python .codex/skills/直播竞品盯播分析/scripts/build_html_dashboard.py \
  --delivery-dir output/live-monitor/账号_直播分析_YYYY-MM-DD_时长 \
  --mode auto
```

The script generates `07_直播分析可视化看板.html` in the delivery root.

Useful arguments:

- `--mode auto|inline|local-js`: default `auto`.
- `--inline-threshold-kb`: auto-mode threshold for structured JSON data, default 180KB.
- `--media-threshold-mb`: auto-mode threshold for local evidence files such as recording and screenshots, default 50MB.
- `--out`: custom HTML output path.
- `--title`: custom dashboard title.

Data mode rules:

- `inline`: embed structured JSON data directly in the HTML.
- `local-js`: write `_internal_技术底稿/html_data/直播分析数据.js` and let the HTML load that local file.
- `auto`: use `inline` only when both structured data and local evidence files are small; otherwise use `local-js`.

Do not embed large recordings or screenshots as base64. The HTML should reference existing local video, screenshot, transcript, and workbook files by relative path. If the user wants to send the dashboard to someone else, tell them to send the whole delivery folder, not just the HTML file.

After generating the dashboard, verify that the page loads KPI cards, timeline events, screenshots, and speech modules. If Playwright is available, use local Chrome or the in-app browser to render-check the file. If a data category is missing, the page should show `暂无数据` instead of failing.

For field expectations and fallback behavior, read `references/html-dashboard.md`.
