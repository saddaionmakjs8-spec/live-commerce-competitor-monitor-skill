# Live Monitor Data Schema

Store cleaned events as newline-delimited JSON in `events.jsonl`. Each line must include:

```json
{"type":"metric_sample","timestamp":"2026-05-18T22:50:50+08:00","online_viewers":29}
```

Use ISO timestamps with timezone when possible. If only clock time is available, include `session_date` in session metadata.

## Common Fields

- `type`: one of the event types below.
- `timestamp`: event time for instant events.
- `start_time`, `end_time`: segment time for speech or longer actions.
- `source`: `douyin_app`, `mobile_mirror`, `browser`, `screen_recording`, `ocr`, `manual`, or `transcript`.
- `evidence`: filename, screenshot path, recording timestamp, or short note.
- `confidence`: `high`, `medium`, `low`.

## Event Types

### session_meta

Use once per run or per chunk.

Fields:

- `platform`
- `account_name`
- `account_id`
- `live_room_url`
- `session_date`
- `chunk_id`
- `capture_method`
- `screen_scope`: `target_window`, `target_region`, `full_display`, `unknown`
- `sample_interval_seconds`
- `min_duration_minutes`: normally `10`
- `stop_reason`: `requested_duration`, `loop_completed`, `manual_stop`, `technical_failure`, `pilot_only`, or `uncertain_loop`
- `capture_quality`: object with `screen`, `audio`, `comments`, `product_card`
- `formal_acceptance`: object with `recording_valid`, `audio_valid`, `transcript_valid`, `screenshots_valid`, `evidence_delivered`

### recording_chunk

Fields:

- `start_time`
- `end_time`
- `duration_seconds`
- `file_path`
- `recording_valid`: true or false
- `audio_valid`: true or false
- `screen_scope`: `target_window`, `target_region`, `full_display`, `unknown`
- `notes`

Use this for every recording file. Screenshots do not replace recording chunks. Formal runs should use `target_window` or `target_region`; `full_display` is fallback evidence only.

### screenshot_event

Fields:

- `timestamp`
- `recording_timecode`
- `file_path`
- `screenshot_reason`: `product_change`, `price_coupon_change`, `order_signal`, `comment_burst`, `visual_scene_change`, `loop_marker`, `trust_claim`, `other`
- `visual_state`: short description of what is visible
- `changed_from`: previous visible state when useful
- `product_id`
- `product_title`

Filename rule:

```text
raw/screenshots/HH-MM-SS_short-visible-content.png
```

If timecode is unavailable, use:

```text
raw/screenshots/YYYYMMDD-HHMMSS_short-visible-content.png
```

Keep slugs short and readable, such as `product-card-1hao-1299`, `loop-start-gold-box-closeup`, or `coupon-gift-heart-card`.

### metric_sample

Fields:

- `online_viewers`
- `cumulative_viewers`
- `likes`
- `popularity`
- `hot_sale_count`
- `comment_visible_count`
- `product_id`
- `product_title`
- `product_price`

Use null for unavailable fields. Do not invent missing numbers.

### speech_segment

Fields:

- `start_time`
- `end_time`
- `speaker`: `anchor`, `co_anchor`, `official_chat`, `assistant`, `unknown`
- `speech_type`: see SKILL.md classification list
- `quote`
- `quote_confidence`: `exact_audio`, `exact_visible_text`, `approximate`, `paraphrase`
- `product_id`
- `product_title`
- `sales_intent`: short Chinese phrase such as `引导点1号链接`, `强调官方保障`, `推优惠券`

For word-for-word transcripts, `quote_confidence` must be `exact_audio` and `evidence` must point to transcript/audio timecode. `exact_visible_text` is allowed for official chat or burned-in text, but it is not a spoken transcript.

### product_event

Fields:

- `event_kind`: `product_switch`, `price_change`, `coupon_drop`, `stock_claim`, `limited_time`, `bundle`, `shipping`, `gift`, `sold_count_change`
- `product_id`
- `link_number`
- `product_title`
- `price`
- `coupon`
- `claim_text`

### comment_event

Fields:

- `commenter`
- `comment_text`
- `comment_type`: `buyer_question`, `price_question`, `quality_question`, `shipping_question`, `coupon_question`, `social_proof`, `complaint`, `greeting`, `other`
- `related_product_id`
- `response_observed`: true or false

### order_signal

Fields:

- `signal_kind`: `order_popup`, `sold_count_change`, `hot_sale_count_change`, `stock_change`, `cart_rank_change`, `anchor_claim`, `unknown`
- `product_id`
- `product_title`
- `value_before`
- `value_after`
- `signal_text`
- `verified_order_count`: true or false

### loop_marker

Fields:

- `marker_id`
- `loop_id`
- `marker_kind`: `probable_start`, `repeat_visual`, `repeat_speech`, `repeat_product_sequence`, `probable_completion`
- `timestamp`
- `recording_timecode`
- `segment_name`: short label such as `gold-box-closeup`, `host-holds-32-box`, `1hao-product-card`
- `evidence`
- `matched_previous_marker_id`
- `similarity_basis`: what matched, such as `same_frame`, `same_speech`, `same_product_sequence`, `same_transition_timing`
- `loop_started_at`
- `loop_completed_at`
- `min_duration_satisfied`: true or false

## Example

```jsonl
{"type":"session_meta","timestamp":"2026-05-18T22:50:00+08:00","platform":"Douyin","account_name":"费列罗官方旗舰店","capture_method":"douyin_app_screen_recording","sample_interval_seconds":30,"min_duration_minutes":10,"capture_quality":{"screen":"ok","audio":"ok","comments":"ok","product_card":"ok"}}
{"type":"recording_chunk","start_time":"2026-05-18T22:50:00+08:00","end_time":"2026-05-18T23:20:00+08:00","duration_seconds":1800,"file_path":"raw/screen-recording-001.mov","recording_valid":true,"audio_valid":true}
{"type":"screenshot_event","timestamp":"2026-05-18T22:50:12+08:00","recording_timecode":"00:00:12","file_path":"raw/screenshots/00-00-12_product-card-1hao-1299.png","screenshot_reason":"product_change","visual_state":"1号链接三色球商品卡，大促价129.9"}
{"type":"metric_sample","timestamp":"2026-05-18T22:50:50+08:00","online_viewers":29,"likes":7718,"hot_sale_count":218,"product_title":"费列罗臻品巧克力32粒装三色球","product_price":129.9,"source":"ocr"}
{"type":"speech_segment","start_time":"2026-05-18T22:51:02+08:00","end_time":"2026-05-18T22:51:18+08:00","speaker":"official_chat","speech_type":"product_intro","quote":"1号链接三色球三种口味：经典小金球+朗姆黑巧+拉斐尔椰蓉","quote_confidence":"exact_visible_text","sales_intent":"介绍口味并引导1号链接"}
{"type":"comment_event","timestamp":"2026-05-18T22:51:25+08:00","commenter":"风*****","comment_text":"有没有优惠券","comment_type":"coupon_question","response_observed":false}
{"type":"order_signal","timestamp":"2026-05-18T22:51:50+08:00","signal_kind":"hot_sale_count_change","product_title":"费列罗臻品巧克力32粒装三色球","value_before":218,"value_after":220,"verified_order_count":false}
{"type":"loop_marker","marker_id":"loop1-start","loop_id":"loop1","marker_kind":"probable_start","timestamp":"2026-05-18T22:50:12+08:00","recording_timecode":"00:00:12","segment_name":"product-card-1hao-1299","evidence":"raw/screenshots/00-00-12_product-card-1hao-1299.png"}
```
