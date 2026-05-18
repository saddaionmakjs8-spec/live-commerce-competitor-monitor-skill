#!/usr/bin/env python3
"""Build structured CSV tables and a first-pass summary from live monitor JSONL."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVENT_TYPES = [
    "session_meta",
    "recording_chunk",
    "screenshot_event",
    "metric_sample",
    "speech_segment",
    "product_event",
    "comment_event",
    "order_signal",
    "loop_marker",
]


CSV_FIELDS = {
    "session_meta": [
        "timestamp",
        "platform",
        "account_name",
        "account_id",
        "live_room_url",
        "session_date",
        "chunk_id",
        "capture_method",
        "screen_scope",
        "sample_interval_seconds",
        "min_duration_minutes",
        "stop_reason",
        "capture_quality",
        "formal_acceptance",
        "source",
        "evidence",
        "confidence",
    ],
    "recording_chunk": [
        "start_time",
        "end_time",
        "duration_seconds",
        "file_path",
        "recording_valid",
        "audio_valid",
        "screen_scope",
        "notes",
        "source",
        "evidence",
        "confidence",
    ],
    "screenshot_event": [
        "timestamp",
        "recording_timecode",
        "file_path",
        "screenshot_reason",
        "visual_state",
        "changed_from",
        "product_id",
        "product_title",
        "source",
        "evidence",
        "confidence",
    ],
    "metric_sample": [
        "timestamp",
        "online_viewers",
        "cumulative_viewers",
        "likes",
        "popularity",
        "hot_sale_count",
        "comment_visible_count",
        "product_id",
        "product_title",
        "product_price",
        "source",
        "evidence",
        "confidence",
    ],
    "speech_segment": [
        "start_time",
        "end_time",
        "speaker",
        "speech_type",
        "quote",
        "quote_confidence",
        "sales_intent",
        "product_id",
        "product_title",
        "source",
        "evidence",
        "confidence",
        "online_before",
        "online_after",
        "online_delta",
        "likes_before",
        "likes_after",
        "likes_delta",
        "order_signals_after",
    ],
    "product_event": [
        "timestamp",
        "event_kind",
        "product_id",
        "link_number",
        "product_title",
        "price",
        "coupon",
        "claim_text",
        "source",
        "evidence",
        "confidence",
    ],
    "comment_event": [
        "timestamp",
        "commenter",
        "comment_text",
        "comment_type",
        "related_product_id",
        "response_observed",
        "source",
        "evidence",
        "confidence",
    ],
    "order_signal": [
        "timestamp",
        "signal_kind",
        "product_id",
        "product_title",
        "value_before",
        "value_after",
        "signal_text",
        "verified_order_count",
        "source",
        "evidence",
        "confidence",
    ],
    "loop_marker": [
        "marker_id",
        "loop_id",
        "marker_kind",
        "timestamp",
        "recording_timecode",
        "segment_name",
        "evidence",
        "matched_previous_marker_id",
        "similarity_basis",
        "loop_started_at",
        "loop_completed_at",
        "min_duration_satisfied",
        "source",
        "confidence",
    ],
}

CSV_FILENAMES = {
    "session_meta": "session_meta.csv",
    "recording_chunk": "recording_chunks.csv",
    "screenshot_event": "screenshot_events.csv",
    "metric_sample": "metric_samples.csv",
    "speech_segment": "speech_segments.csv",
    "product_event": "product_events.csv",
    "comment_event": "comment_events.csv",
    "order_signal": "order_signals.csv",
    "loop_marker": "loop_markers.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True, help="Path to events.jsonl")
    parser.add_argument("--out-dir", required=True, help="Directory for CSV and summary outputs")
    parser.add_argument("--post-window-seconds", type=int, default=120)
    return parser.parse_args()


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            if fmt == "%H:%M:%S":
                return None
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON on line {line_no}: {exc}") from exc
        record.setdefault("type", "unknown")
        events.append(record)
    return events


def numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    multiplier = 1.0
    if text.endswith("万"):
        multiplier = 10000.0
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def nearest_metric(metrics: list[dict[str, Any]], target: datetime | None, direction: str) -> dict[str, Any] | None:
    if target is None:
        return None
    candidates = []
    for metric in metrics:
        ts = parse_time(metric.get("timestamp"))
        if ts is None:
            continue
        if direction == "before" and ts <= target:
            candidates.append((abs((target - ts).total_seconds()), metric))
        elif direction == "after" and ts >= target:
            candidates.append((abs((ts - target).total_seconds()), metric))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def count_order_signals_after(order_signals: list[dict[str, Any]], start: datetime | None, end: datetime | None, window_seconds: int) -> int:
    if start is None:
        return 0
    upper = end or start
    count = 0
    for signal in order_signals:
        ts = parse_time(signal.get("timestamp"))
        if ts is None:
            continue
        if start <= ts and (ts - upper).total_seconds() <= window_seconds:
            count += 1
    return count


def enrich_speech(events_by_type: dict[str, list[dict[str, Any]]], post_window_seconds: int) -> None:
    metrics = sorted(events_by_type["metric_sample"], key=lambda item: str(item.get("timestamp", "")))
    order_signals = events_by_type["order_signal"]
    for speech in events_by_type["speech_segment"]:
        start = parse_time(speech.get("start_time") or speech.get("timestamp"))
        end = parse_time(speech.get("end_time")) or start
        before = nearest_metric(metrics, start, "before")
        after = nearest_metric(metrics, end, "after")
        for field in ("online_viewers", "likes"):
            before_value = numeric(before.get(field)) if before else None
            after_value = numeric(after.get(field)) if after else None
            short = "online" if field == "online_viewers" else "likes"
            speech[f"{short}_before"] = before_value
            speech[f"{short}_after"] = after_value
            speech[f"{short}_delta"] = None if before_value is None or after_value is None else after_value - before_value
        speech["order_signals_after"] = count_order_signals_after(order_signals, start, end, post_window_seconds)


def write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def make_summary(events_by_type: dict[str, list[dict[str, Any]]]) -> str:
    meta = events_by_type["session_meta"][0] if events_by_type["session_meta"] else {}
    metrics = events_by_type["metric_sample"]
    speech = events_by_type["speech_segment"]
    comments = events_by_type["comment_event"]
    orders = events_by_type["order_signal"]
    products = events_by_type["product_event"]
    recordings = events_by_type["recording_chunk"]
    screenshots = events_by_type["screenshot_event"]
    loops = events_by_type["loop_marker"]

    online_values = [numeric(item.get("online_viewers")) for item in metrics]
    online_values = [v for v in online_values if v is not None]
    like_values = [numeric(item.get("likes")) for item in metrics]
    like_values = [v for v in like_values if v is not None]

    speech_types = Counter(item.get("speech_type") or "unknown" for item in speech)
    comment_types = Counter(item.get("comment_type") or "unknown" for item in comments)
    order_types = Counter(item.get("signal_kind") or "unknown" for item in orders)
    screenshot_reasons = Counter(item.get("screenshot_reason") or "unknown" for item in screenshots)
    loop_kinds = Counter(item.get("marker_kind") or "unknown" for item in loops)
    top_quotes = Counter((item.get("quote") or "").strip() for item in speech if (item.get("quote") or "").strip()).most_common(10)
    screen_scopes = Counter((item.get("screen_scope") or "unknown") for item in recordings)
    audio_valid_count = sum(1 for item in recordings if str(item.get("audio_valid", "")).lower() == "true")
    capture_quality = meta.get("capture_quality") or {}
    formal_acceptance = meta.get("formal_acceptance") or {}

    lines = [
        "# Live Commerce Competitor Monitor Summary",
        "",
        "## Data Scope",
        "",
        f"- Platform: {meta.get('platform', '')}",
        f"- Account: {meta.get('account_name', '')}",
        f"- Capture method: {meta.get('capture_method', '')}",
        f"- Screen scope: {meta.get('screen_scope', '')}",
        f"- Stop reason: {meta.get('stop_reason', '')}",
        f"- Capture quality: {capture_quality}",
        f"- Formal acceptance: {formal_acceptance}",
        f"- Recording chunks: {len(recordings)}",
        f"- Screenshot events: {len(screenshots)}",
        f"- Loop markers: {len(loops)}",
        f"- Metric samples: {len(metrics)}",
        f"- Speech segments: {len(speech)}",
        f"- Product events: {len(products)}",
        f"- Comment events: {len(comments)}",
        f"- Order signals: {len(orders)}",
        "",
        "## Metric Range",
        "",
    ]
    if online_values:
        lines.append(f"- Online viewers: min {min(online_values):g}, max {max(online_values):g}, first {online_values[0]:g}, last {online_values[-1]:g}")
    if like_values:
        lines.append(f"- Likes: first {like_values[0]:g}, last {like_values[-1]:g}, delta {like_values[-1] - like_values[0]:g}")
    if not online_values and not like_values:
        lines.append("- No numeric metric range available.")

    lines += ["", "## Recording Evidence", ""]
    if recordings:
        valid_seconds = sum(numeric(item.get("duration_seconds")) or 0 for item in recordings if str(item.get("recording_valid", "")).lower() != "false")
        lines.append(f"- Valid recording duration: {valid_seconds:g} seconds")
        lines.append("- Recording files: " + ", ".join(str(item.get("file_path", "")) for item in recordings if item.get("file_path")))
        lines.append("- Recording screen scopes: " + ", ".join(f"{k}={v}" for k, v in screen_scopes.most_common()))
        lines.append(f"- Recording chunks with valid audio: {audio_valid_count}/{len(recordings)}")
    else:
        lines.append("- No recording chunks recorded.")
    if screenshot_reasons:
        lines.append("- Screenshot reasons: " + ", ".join(f"{k}={v}" for k, v in screenshot_reasons.most_common()))
    else:
        lines.append("- Screenshot reasons: none")

    lines += ["", "## Loop Markers", ""]
    if loop_kinds:
        lines.append("- Loop marker kinds: " + ", ".join(f"{k}={v}" for k, v in loop_kinds.most_common()))
        completion = [item for item in loops if item.get("marker_kind") == "probable_completion"]
        lines.append(f"- Probable loop completions: {len(completion)}")
    else:
        lines.append("- No loop markers recorded.")

    lines += ["", "## Speech Types", ""]
    if speech_types:
        for key, count in speech_types.most_common():
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- No speech segments recorded.")

    lines += ["", "## Top Quotes", ""]
    if top_quotes:
        for quote, count in top_quotes:
            lines.append(f"- {count}x {quote}")
    else:
        lines.append("- No quotes recorded.")

    lines += ["", "## Comments And Order Signals", ""]
    if comment_types:
        lines.append("- Comment types: " + ", ".join(f"{k}={v}" for k, v in comment_types.most_common()))
    else:
        lines.append("- Comment types: none")
    if order_types:
        lines.append("- Order signal types: " + ", ".join(f"{k}={v}" for k, v in order_types.most_common()))
    else:
        lines.append("- Order signal types: none")

    lines += [
        "",
        "## Review Notes",
        "",
        "- Treat this as a first-pass structural summary.",
        "- Manually review speech-to-metric relationships before making business claims.",
        "- Use causal language only when patterns repeat across comparable windows.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    events = load_events(Path(args.events))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    events_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_type[event.get("type", "unknown")].append(event)

    enrich_speech(events_by_type, args.post_window_seconds)

    for event_type, fields in CSV_FIELDS.items():
        write_csv(out_dir / CSV_FILENAMES[event_type], events_by_type[event_type], fields)

    (out_dir / "summary.md").write_text(make_summary(events_by_type), encoding="utf-8")
    print(f"Wrote report files to {out_dir}")


if __name__ == "__main__":
    main()
