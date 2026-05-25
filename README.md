# Discord Moderation Bot — Autonomous Community Manager Agent

An asynchronous Discord bot that watches live chat, scores every message for
**toxicity, sentiment, and emotion**, and applies **statistical process control
(SPC)** to each user's behaviour over time. When a user's rolling score drifts
out of control, the bot uses a generative AI model to write a contextual
warning and posts it back to the channel — acting as a fully autonomous
community manager.

> Course project for *WIF3009 — Python for Scientific Computing*.

---

## Features

- **Live NLP scoring** of every message — toxicity, sentiment, and emotion via
  Hugging Face Inference APIs, with a local `transformers` fallback when the API
  is unavailable.
- **Per-user, per-channel SPC** — an EWMA (Exponentially Weighted Moving
  Average) of a combined *Composite Linguistic Index (CLI)* tracks each user
  against a baseline learned from the channel's own healthy history.
- **Adaptive thresholds** — four escalating actions (`ignore`, `soft_reminder`,
  `warning`, `escalate`) chosen from statistical control limits, not hardcoded
  cutoffs.
- **Generative replies** — Google Gemini drafts a formal, theme-aware warning
  (without repeating the offensive content) only when an intervention is needed.
- **Persistent storage** — PostgreSQL records users, messages, interventions,
  and server metrics for auditing and future calibration.
- **Resilient by design** — NLP, AI, and database failures are caught
  individually so a single failure never crashes the bot.

---

## How it works

```
User sends a message
        │
        ▼
 analyze_text()        toxicity + sentiment + emotion  (HF API → local fallback)
        │
        ▼
 Aggregator            combine scores into a CLI, update the user's EWMA
        │
        ▼
 AdaptiveThreshold     compare EWMA to statistical control limits → pick an action
        │
        ▼
 ResponseGenerator     if action ≠ ignore, Gemini drafts a contextual warning
        │
        ▼
 Bot replies in channel + everything is logged to PostgreSQL
```

The orchestration lives in [bot/pipeline.py](bot/pipeline.py); the Discord event
loop is in [bot/event_handler.py](bot/event_handler.py).

---

## Project structure

```
moderation-bot/
├── bot/
│   ├── main.py                 # entrypoint: load settings, start the bot
│   ├── config.py               # .env loading + Discord intents
│   ├── event_handler.py        # discord.Client — on_ready / on_message / shutdown
│   ├── pipeline.py             # glue layer: analyze → decide → store → reply
│   ├── moderation/
│   │   ├── analyzer.py         # runs all three NLP models, merges results
│   │   ├── sentiment.py        # HF sentiment (cardiffnlp/twitter-roberta)
│   │   ├── toxicity.py         # HF toxicity (citizenlab/distilbert multilingual)
│   │   ├── emotion.py          # HF emotion (tabularisai multilingual)
│   │   ├── fallback_model.py   # local transformers models (offline fallback)
│   │   ├── hf_client.py        # raw HF REST helper
│   │   ├── intervention.py     # Moderator — make_decision()
│   │   └── response_generator.py  # Gemini warning-text generator
│   ├── analytics/
│   │   ├── aggregation.py      # Aggregator (EWMA/CLI) + AggregatorData (DB reads)
│   │   └── threshold.py        # AdaptiveThreshold + ActionType
│   └── utils/
│       └── logger.py           # file + console logging
├── db/
│   ├── database.py             # asyncpg connection pool (global `db`)
│   ├── queries.py              # all SQL: users, messages, interventions, stats
│   ├── seed.py                 # insert sample data for local testing
│   └── migrations/init.sql     # schema (run automatically by Docker)
├── tests/                      # pytest suites + ad-hoc API/NLP scripts
├── docker-compose.yml          # PostgreSQL 15 service
├── requirements.txt
└── .env.example
```

---

## Tech stack

| Concern            | Tool |
|--------------------|------|
| Bot framework      | [discord.py](https://discordpy.readthedocs.io/) (async) |
| NLP (primary)      | Hugging Face Inference API via `huggingface_hub` |
| NLP (fallback)     | `transformers` + `torch` (runs locally) |
| Generative replies | Google Gemini (`google-genai`, `gemini-2.5-flash-lite`) |
| Database           | PostgreSQL 15 + `asyncpg` |
| Analytics / SPC    | `numpy`, `pandas`, `scipy` |
| Config             | `python-dotenv` |
| Tests              | `pytest`, `pytest-asyncio` |

---

## Prerequisites

- **Python 3.11+** (the code uses `StrEnum`; developed on Python 3.13)
- **Docker Desktop** (for PostgreSQL) — or a local PostgreSQL 15 install
- A **Discord application / bot token**
- A **Hugging Face access token**
- A **Google Gemini API key**

---

## Setup

### 1. Clone and create a virtual environment

```powershell
git clone <repo-url>
cd moderation-bot

python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
# source .venv/bin/activate      # macOS / Linux
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

> `torch` is a large download and is only used as the offline NLP fallback. The
> bot runs on the Hugging Face API by default.

### 3. Configure environment variables

Copy the example file and fill in your secrets:

```powershell
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

| Variable            | Used by | How to get it |
|---------------------|---------|---------------|
| `DISCORD_TOKEN`     | bot login | [Discord Developer Portal](https://discord.com/developers/applications) → your app → **Bot** → Reset Token |
| `HF_API_KEY`        | sentiment / toxicity / emotion | [huggingface.co](https://huggingface.co/settings/tokens) → Settings → Access Tokens |
| `GENERATIVE_AI_API` | warning generation | [Google AI Studio](https://aistudio.google.com/app/apikey) → Get API key |
| `DB_PASSWORD`       | PostgreSQL container | choose any password (must match `DATABASE_URL`) |
| `DATABASE_URL`      | bot DB connection | `postgresql://postgres:<DB_PASSWORD>@localhost:5432/modbot` |

### 4. Set up the Discord bot

1. In the Developer Portal, open your app → **Bot**.
2. Enable the **Message Content Intent** (required — the bot reads message text).
3. Invite the bot to your server via **OAuth2 → URL Generator** with the `bot`
   scope and *Send Messages* / *Read Message History* permissions.

### 5. Start the database

```powershell
docker compose up -d
```

This launches PostgreSQL 15 and runs [db/migrations/init.sql](db/migrations/init.sql)
automatically on first boot, creating all tables and indexes.

(Optional) load sample data for local testing:

```powershell
python -m db.seed
```

---

## Running the bot

```powershell
python -m bot.main
```

On startup the bot connects to PostgreSQL, registers every guild it's in, and
prints `Bot is online.` It then scores each new message and replies only when an
intervention is warranted. Logs are written to `moderator.log` and the console.

---

## Database schema

Tables are created by [db/migrations/init.sql](db/migrations/init.sql). The
foreign-key chain enforces insert order:

```
moderation_settings (guild)
        ↓
      users
        ↓
     messages   (needs guild + user)
        ↓
  interventions (needs guild + user + message)
```

| Table                 | Purpose |
|-----------------------|---------|
| `moderation_settings` | one row per Discord guild |
| `users`               | per-user totals, `rolling_toxicity_avg`, `last_ewma`, `warning_count` |
| `messages`            | every analyzed message with its scores |
| `interventions`       | each action taken, severity, reasoning, generated reply |
| `server_metrics`      | rolling SPC stats per guild (for a future dashboard) |

---

## The moderation algorithm

The scoring logic lives in [bot/analytics/aggregation.py](bot/analytics/aggregation.py)
and [bot/analytics/threshold.py](bot/analytics/threshold.py). For the full
breakdown — data contracts, CLI/EWMA math, emotion mapping, and control-limit
formulas — see **[docs/MODERATION_LOGIC.md](docs/MODERATION_LOGIC.md)**.

1. **CLI (Composite Linguistic Index)** — each message's toxicity, sentiment,
   and emotion are fused into a single `[0, 1]` score. Weights default to
   **toxicity 0.5 / sentiment 0.3 / emotion 0.2**, but a signal is down-weighted
   when its model confidence is below `0.7`, so unreliable scores can't dominate.
   - Sentiment is mapped to `[0, 1]` via `(1 - sentiment_score) / 2`, so *more
     negative sentiment → higher CLI*.
   - Emotion is mapped using a PAD-inspired table (`contempt`/`disgust`/`anger`
     score highest; `joy`/`love`/`gratitude` near zero).
2. **EWMA** — `ewma = λ·cli + (1 − λ)·prev_ewma` (default `λ = 0.40`) gives a
   per-user rolling score that weighs recent messages more heavily. A user who
   sends many mildly toxic messages is flagged even if no single message crosses
   a limit.
3. **Baseline (`start_up`)** — when a channel's `Moderator` is first created, it
   learns `μ` and `σ` of the CLI from up to 200 of that channel's *healthy*
   historical messages (low toxicity, non-negative sentiment, no high-confidence
   anger/contempt/disgust).
4. **Adaptive thresholds** — control limits are
   `μ + z(α)·σ·√(λ / (2 − λ))`, where each action has its own significance
   level `α` (`soft_reminder` 0.05, `warning` 0.001, `escalate` 0.00001). The
   EWMA is compared against these to pick `escalate` > `warning` >
   `soft_reminder` > `ignore`.

### Decision input / output

`Moderator.make_decision()` consumes a cleaned message dict and returns:

```python
{
    'user_id': ...,
    'guild_id': ...,
    'channel_id': ...,
    'message_id': ...,
    'action_type': 'ignore' | 'soft_reminder' | 'warning' | 'escalate',
    'reasoning': '...',              # why, from Gemini (empty if ignored)
    'generated_response': '...',     # the reply text (empty if ignored)
    'created_at': '<iso timestamp>',
    'metrics': { '<action>': <threshold>, ... },
    'ewma': <float>,
}
```

---

## Testing

```powershell
pytest
```

- [tests/test_spc.py](tests/test_spc.py) and
  [tests/test_intervention.py](tests/test_intervention.py) are pure unit tests
  (no network or DB required).
- [tests/test_pipeline.py](tests/test_pipeline.py) exercises the full pipeline —
  it needs a running database and valid API keys for the non-mocked path.
- [tests/test_nlp.py](tests/test_nlp.py) and [tests/test_api.py](tests/test_api.py)
  are ad-hoc scripts (run with `python -m tests.test_nlp`) that hit the live HF
  API and print results.

---

## Troubleshooting

- **`HF_API_KEY is missing in .env file`** — `.env` isn't present or the key is
  blank. Copy `.env.example` to `.env` and fill it in.
- **`DISCORD_TOKEN is not set`** — same; the token is required to log in.
- **Bot connects but never reads messages** — the *Message Content Intent* is
  not enabled in the Developer Portal.
- **Database connection errors** — make sure `docker compose up -d` is running
  and `DATABASE_URL`'s password matches `DB_PASSWORD`.
- **First run is slow / downloads models** — the local `transformers` fallback
  downloads model weights on first use; this only happens if the HF API path
  fails.

---

## Ethical note

Automated moderation carries real risks: NLP models can misclassify sarcasm,
dialect, or other languages, and an over-eager bot can chill legitimate
conversation. This project mitigates that by (a) acting on *patterns over time*
rather than single messages, (b) down-weighting low-confidence model output, and
(c) calibrating thresholds to each channel's own norms. Human moderators should
still review escalations — the bot is an assistant, not a final authority.
