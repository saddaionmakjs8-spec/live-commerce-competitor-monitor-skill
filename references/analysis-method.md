# Analysis Method

Use this reference when converting event logs into business conclusions.

## Unit of Analysis

Use two linked units:

1. `time_window`: 30-second or 1-minute blocks with metrics and visible room state.
2. `speech_event`: a sales-intent segment with pre/post metric comparison.

Do not analyze a phrase without its context:

- active product
- price/coupon state
- online viewers before/after
- comments before/after
- order signals before/after
- whether the room was in a traffic spike, stable period, or decline

## Relationship Labels

Use these labels:

- `viewer_growth_nearby`: online viewers rose after or during the segment.
- `viewer_loss_nearby`: online viewers fell after or during the segment.
- `comment_burst_nearby`: comments/questions increased nearby.
- `order_signal_nearby`: order/hot-sale/sold-count signal moved nearby.
- `no_visible_effect`: no visible movement in tracked fields.
- `confounded`: product switch, platform traffic injection, giveaway, or technical interruption makes attribution unclear.

## High-Value Patterns

Prioritize patterns that repeat:

- CTA plus product-card change.
- Price/coupon line followed by buyer questions or order signals.
- Trust/official-store line before conversion in low-trust categories.
- Objection answer followed by comment decline or order signal.
- Scene/emotion line that holds viewers but does not create orders.
- Social proof line that coincides with order-signal bursts.

## Common Mistakes

- Do not call hot-sale count a verified order count unless verified.
- Do not treat likes as purchases.
- Do not summarize comments only by sentiment; buyer-intent questions matter more.
- Do not average the whole session and miss short conversion windows.
- Do not compare one live room's absolute viewer count against another without account-size context.

## Final Judgment Template

```text
在 [time range]，主播/官方反复使用 [speech pattern]。
该话术主要服务于 [sales intent]，当时主推 [product/price/coupon]。
附近 [pre/post window] 内，在线人数从 [x] 到 [y]，评论出现 [comment pattern]，订单信号为 [signal]。
因此它更像是 [拉停留 / 拉互动 / 解疑虑 / 促下单 / 维持氛围] 的话术。
证据强度：[strong/medium/weak/unknown]。
```
