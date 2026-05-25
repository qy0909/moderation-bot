# Moderation Logic & Data Contracts

Technical reference for the scoring and decision engine. The implementation lives
in:

- [bot/moderation/intervention.py](../bot/moderation/intervention.py) — `Moderator.make_decision()`
- [bot/analytics/aggregation.py](../bot/analytics/aggregation.py) — `Aggregator` (CLI + EWMA) and `AggregatorData` (DB reads)
- [bot/analytics/threshold.py](../bot/analytics/threshold.py) — `AdaptiveThreshold` + `ActionType`
- [bot/moderation/response_generator.py](../bot/moderation/response_generator.py) — Gemini warning text

---

## 1. Data contracts

### 1.1 `make_decision()` input

`Moderator.make_decision(message, record=...)` receives a `message` dict and
normalizes it with `_clean_input()`. The cleaner reads these raw keys and clamps
each value into a valid range:

| Cleaned field          | Source key             | Range / type        |
|------------------------|------------------------|---------------------|
| `guild_id`             | `guild_id`             | int / str           |
| `channel_id`           | `channel_id`           | int / str           |
| `user_id`              | `user_id`              | int / str           |
| `message_id`           | `message_id`           | int / str           |
| `message_content`      | `text`                 | str                 |
| `toxicity_score`       | `toxicity`             | clamped to `[0, 1]` |
| `toxicity_confidence`  | `toxicity_confidence`  | clamped to `[0, 1]` |
| `sentiment_score`      | `sentiment`            | clamped to `[-1, 1]`|
| `sentiment_confidence` | `sentiment_confidence` | clamped to `[0, 1]` |
| `emotion`              | `emotion`              | str (default `neutral`) |
| `emotion_confidence`   | `emotion_confidence`   | clamped to `[0, 1]` |

The normalized dict looks like:

```python
cleaned = {
    'guild_id':             message.get('guild_id'),
    'channel_id':           message.get('channel_id'),
    'user_id':              message.get('user_id'),
    'message_id':           message.get('message_id'),
    'message_content':      str(message.get('text', '')),
    'toxicity_score':       max(0.0, min(1.0, float(message.get('toxicity', 0)))),
    'toxicity_confidence':  max(0.0, min(1.0, float(message.get('toxicity_confidence', 0)))),
    'sentiment_score':      max(-1.0, min(1.0, float(message.get('sentiment', 0)))),
    'sentiment_confidence': max(0.0, min(1.0, float(message.get('sentiment_confidence', 0)))),
    'emotion':              str(message.get('emotion', 'neutral')),
    'emotion_confidence':   max(0.0, min(1.0, float(message.get('emotion_confidence', 0)))),
}
```

The optional `record` argument is the user's prior state fetched from the
database (`fetch_user_messages` → the row's `last_ewma`). It seeds the EWMA when
the user has no in-memory history yet.

### 1.2 `make_decision()` output

```python
{
    'user_id':            clean_message.get('user_id'),
    'guild_id':           clean_message.get('guild_id'),
    'channel_id':         clean_message.get('channel_id'),
    'message_id':         clean_message.get('message_id'),
    'action_type':        action_type.value,          # ignore | soft_reminder | warning | escalate
    'reasoning':          reason,                      # from Gemini; '' when ignored
    'generated_response': reply,                       # the warning text; '' when ignored
    'created_at':         datetime.now(timezone.utc).isoformat(),
    'metrics':            { action.value: threshold for action, threshold in thresholds.items() },
    'ewma':               result.get('ewma'),
}
```

`generated_response` / `reasoning` are only populated when `action_type` is not
`ignore`.

---

## 2. Usage / pipeline order

1. **Fetch baseline data** via `AggregatorData.fetch_start_up_message()` — the
   baseline messages must be *normal / healthy / in-control* (the query filters
   to low toxicity, non-negative sentiment, and no high-confidence
   anger/contempt/disgust).
2. **Create an `Aggregator`** and calibrate it: `aggregator.start_up(messages)`.
3. **Create an `AdaptiveThreshold`.**
4. **Create a `ResponseGenerator`.**
5. **Create a `Moderator(aggregator, threshold, response_generator)`.**
6. **Decide:** `output = await moderator.make_decision(msg, record=record)` where
   `record` comes from `fetch_user_messages`.

This is exactly what [bot/pipeline.py](../bot/pipeline.py) wires up per channel
(`_get_moderator` builds and calibrates one `Moderator` per `channel_id`).

---

## 3. Scoring logic

### 3.1 CLI — Composite Linguistic Index

Each message is reduced to a single score in `[0, 1]` by fusing toxicity,
sentiment, and emotion. The default weighting reflects their reliability as
toxicity signals:

```
toxicity : sentiment : emotion  =  0.5 : 0.3 : 0.2
```

### 3.2 Confidence gating (the "trust score")

A signal is only trusted at full weight when its model confidence is **> 0.7**.
For any signal below that threshold, its raw score is multiplied by its own
confidence and the denominator is re-normalized, so an unreliable model can't
dominate the CLI. Toxicity is also given a floor — when toxicity is trusted, the
CLI can never fall below the raw toxicity score (`cli = max(cli, t_s)`). This
encodes the priority *reliable > unreliable*, and *toxicity > sentiment >
emotion*.

### 3.3 Sentiment mapping

Sentiment arrives in `[-1, 1]` and is mapped into `[0, 1]` with:

```
s_processed = (1 - sentiment_score) / 2
```

so a **more negative** sentiment produces a **higher** CLI contribution.

### 3.4 Emotion mapping (PAD-inspired)

Emotions are mapped to a severity weight using the
**Pleasure–Arousal–Dominance (PAD)** model: low pleasure (−P), low dominance
(−D), and high/low arousal (±A) are treated as most negative. Pleasure behaves
like the sentiment score; the low-dominance cluster `{anger, contempt, disgust}`
scores highest.

| Emotion     | Weight |
|-------------|--------|
| contempt    | 0.95 |
| disgust     | 0.85 |
| anger       | 0.75 |
| fear        | 0.55 |
| sadness     | 0.50 |
| frustration | 0.35 |
| surprise    | 0.02 |
| gratitude   | 0.02 |
| joy         | 0.01 |
| neutral     | 0.00 |
| love        | 0.00 |

### 3.5 EWMA — per-user rolling score

```
current_ewma = λ · current_cli + (1 − λ) · previous_ewma          (λ default = 0.40)
```

`λ` is the weight given to the current message relative to history. A higher `λ`
reacts faster; a lower `λ` smooths more. The EWMA is tracked **per user per
channel**, so a pattern of mildly toxic messages is caught even when no single
message is severe.

### 3.6 Baseline calibration (`start_up`)

`start_up()` computes the channel's normal-behaviour statistics from healthy
historical messages:

- `avg` = mean CLI of the baseline (`μ`)
- `std` = standard deviation of the baseline CLI, floored at `0.02` (`σ`)
- the last baseline EWMA seeds new users' starting point.

### 3.7 Adaptive thresholds (SPC control limits)

Thresholds are EWMA control limits derived from the baseline, computed in
`AdaptiveThreshold.get_thresholds()`:

```
threshold(action) = μ + z(α) · σ · √( λ / (2 − λ) )
```

- `μ`, `σ` come from `start_up`.
- `√(λ / (2 − λ))` converts the CLI standard deviation into the **steady-state**
  EWMA standard deviation. (The full finite-sample form multiplies this by a
  start-up term `1 − (1 − λ)^{2t}` that → 1 as the message count `t → ∞`; the
  code uses the asymptotic limit.)
- `z(α) = norm.ppf(1 − α)` is the normal-distribution multiplier for each
  action's significance level:

  | Action          | α (significance) |
  |-----------------|------------------|
  | `ignore`        | 0.15 |
  | `soft_reminder` | 0.05 |
  | `warning`       | 0.001 |
  | `escalate`      | 0.00001 |

A smaller `α` ⇒ a larger `z` ⇒ a higher bar, so `escalate` sits furthest above
the baseline.

### 3.8 Action selection (UCL check)

The current `ewma` is compared against the control limits, highest first:

```
ewma > threshold(escalate)       → ESCALATE
ewma > threshold(warning)        → WARNING
ewma > threshold(soft_reminder)  → SOFT_REMINDER
otherwise                        → IGNORE
```

Only the non-`IGNORE` actions trigger a Gemini-generated reply.

---

## 4. Setup notes

- Generative replies use `google-genai`; see the SDK docs at
  <https://googleapis.github.io/python-genai/>.
- Core analytics dependencies: `numpy`, `pandas`, `scipy`, `google-genai`,
  `python-dotenv` (full list in [requirements.txt](../requirements.txt)).
- The Gemini key is read from `GENERATIVE_AI_API` in `.env`.
