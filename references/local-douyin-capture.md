# Local Douyin App Capture Protocol

Use this protocol for real monitoring runs. A run shorter than 10 minutes is only a technical pilot.

## Setup

1. Open the local Douyin app and navigate to the target live room.
2. Fix the app window size and position. Avoid resizing during the run.
3. Define the capture target before recording:
   - preferred: target app/window capture
   - acceptable: fixed screen region tightly cropped to the Douyin live-room window
   - not acceptable for formal runs: whole desktop/full display capture
4. Save one pilot screenshot as `raw/capture-target-check.png`. It must show the Douyin live-room software view only. If it includes Codex, Terminal, Finder, browser chrome, desktop, or unrelated windows, fix the capture target before continuing.
5. Make sure these areas are visible when possible:
   - live video and subtitle/burned-in text
   - online viewer count or room traffic number
   - like count or room popularity indicator
   - comments
   - product card/cart area
   - order or hot-sale popups
6. Start a 30-60 second pilot recording before the real run.
7. Verify:
   - screen recording is not black
   - recording and screenshots are scoped to the target app/window or tight region
   - audio is present if speech analysis or a word-for-word transcript is required
   - screenshots are readable and not whole-desktop captures
   - comments and product cards are visible enough for OCR/manual transcription

## Complete Recording Requirement

- Record the entire live room app/window/region continuously from the beginning of the task until the stop condition is met.
- Store the recording under `raw/` as `screen-recording-001.mov`, `screen-recording-002.mov`, etc.
- If the recording is split into chunks, log every chunk as a `recording_chunk` event with start time, end time, duration, file path, and whether the chunk is valid.
- Screenshots and accessibility text are evidence indexes. They do not replace the full recording.
- If recording fails, pause the analysis, restart recording, and mark the failed interval in `assumptions.md`.
- Do not call a recording complete if it only captured the operator's desktop. Full-display capture can be kept as raw fallback evidence, but the formal recording must be the target live-room view.

## Audio

macOS usually cannot capture system audio unless an audio route or recording tool supports it. If audio is required:

- Prefer a known working screen recorder that captures app/system audio.
- If using a virtual audio device, verify it with a pilot playback before the long run.
- Do not use the built-in microphone for competitor analysis unless the user explicitly approves ambient capture.
- If audio capture fails and a word-for-word transcript is required, stop before the formal run and mark the task blocked. Do not substitute visible comments or approximate paraphrase for the transcript.
- If the user permits a no-audio observation run, continue with visible text, comments, product cards, and manual paraphrase; set `capture_quality.audio=missing` and `transcript_valid=false`.

### Tested Local Audio Route On This Mac

This machine currently exposes `OrayVirtualAudioDevice` as both an input and output device. For formal Douyin runs that need a transcript:

1. Save the current default output and system-output device IDs.
2. Temporarily route default output and system output to `OrayVirtualAudioDevice`.
3. Record the Douyin window with `screencapture -v -l<windowid> -GOrayVirtualAudioDevice_UID`.
4. Restore the original output devices immediately after recording, even if recording fails.
5. Extract the audio and verify it is not silent. A zero-RMS audio file fails the pilot.

Do not leave the system output on the virtual device after the run.

## Transcript Requirement

For a complete speech deliverable, save:

```text
raw/audio-source-check.txt
raw/transcript_raw.txt
raw/transcript_segments.csv
```

The transcript must be produced from recorded audio, not from screenshots alone. Each transcript segment should include start time, end time, speaker when identifiable, exact quote, confidence, and evidence file/timecode. If automatic transcription is used, manually review high-impact selling lines, price claims, coupon claims, and objections before analysis.

On this machine, the local fallback is MLX Whisper with a cached Chinese-capable model. If OpenAI transcription is unavailable, use local MLX Whisper after extracting the audio track. A transcript file with zero segments is not valid; rerun with a better model or audio route.

## Long-Run Discipline

- Split monitoring into 30-60 minute chunks. Long single files are fragile.
- Save raw recordings immediately after each chunk.
- Create a checkpoint note every chunk:
  - start/end time
  - account/live room
  - product focus
  - whether audio/screen/OCR remained valid
  - any interruptions
- Do not rely on memory for a multi-hour run. Record timestamped events while watching.
- Do not stop before 10 minutes of valid recording.

## Event-Driven Screenshots

Take screenshots when the screen materially changes, not only at a fixed interval. Screenshot triggers include:

- product card appears, disappears, or changes
- product link number changes
- price, coupon, gift, stock, or limited-time claim changes
- host changes product, prop, camera angle, or scene
- comment volume visibly changes or a buyer-intent question appears
- order popup, hot-sale count movement, sold-count movement, or cart-rank movement appears
- loop start marker, loop end marker, or repeated frame is observed
- unusual trust claim, warranty claim, official-store claim, or competitor-relevant wording appears on screen

Use this filename pattern:

```text
raw/screenshots/HH-MM-SS_short-visible-content.png
```

Examples:

```text
00-12-34_product-card-1hao-1299.png
00-18-05_loop-start-gold-box-closeup.png
00-21-42_coupon-gift-heart-card.png
```

The `HH-MM-SS` value is the recording timecode when possible. If only clock time is available, use `YYYYMMDD-HHMMSS_short-visible-content.png`. Also log each file as a `screenshot_event`.

Screenshots must be captured from the same app-window or tight-region source as the video. Whole-desktop screenshots are setup/debug artifacts, not live-room evidence, and must be stored separately from `raw/screenshots/`.

## Loop Detection And Stop Rule

Some brand live rooms are replay-like loops. Detect loops by comparing visual sequence, speech sequence, product order, on-screen copy, and transition timing.

Use `loop_marker` events for:

- probable loop start
- repeated anchor frame or product frame
- repeated speech/opening copy
- repeated product-card sequence
- probable loop completion

Stop only when:

1. at least 10 minutes of valid recording has been captured
2. the loop has returned to the starting marker
3. evidence is strong enough to explain why the loop is complete

If a loop completes before 10 minutes, continue recording until 10 minutes. If the loop is uncertain after 10 minutes, continue until confidence is adequate or mark the stop reason as uncertain.

## Practical Observation Cadence

During stable periods:

- metric sample every 15-30 seconds
- speech segment whenever the selling intent changes
- product event whenever link/card/price/coupon changes
- event-driven screenshot whenever the visible state materially changes

During active selling periods:

- metric sample every 5-10 seconds
- log every CTA, coupon, urgency line, answer to buyer question, order popup, and sold/hot-sale count movement

## Evidence Rules

- Preserve raw recording even after producing the cleaned dataset.
- Put uncertain claims in `assumptions.md`.
- Distinguish:
  - exact quote from audio
  - exact visible text
  - approximate paraphrase
  - inferred sales intent
- Treat order data as `observable_order_signal` unless the platform exposes verified order count.
