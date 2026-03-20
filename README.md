# AI News Telegram Bot

A small **Python** service that pulls recent articles from **configurable RSS feeds**, uses the **OpenAI API** to pick and summarize the most important **AI-related** stories, and delivers a **daily digest** to **Telegram**. It also supports **manual** `/send` from chat and a **one-shot** CLI run.

## Features

- Multi-source RSS ingestion with per-feed error isolation  
- Normalized article model (`title`, `source`, `url`, `published_at`, `snippet`)  
- URL + near-duplicate title deduplication  
- Heuristic pre-ranking, then OpenAI JSON selection + one-line summaries  
- Telegram **HTML** formatting (reliable; avoids MarkdownV2 escaping pitfalls)  
- **APScheduler** via `python-telegram-bot` **JobQueue** for a daily job  
- Logging for fetch, selection, send, and errors  
- Env-based configuration (`pydantic-settings`)

## Project layout

```text
ai-news-telegram-bot/
├── app/
│   ├── main.py              # CLI: bot + scheduler, or --once
│   ├── config.py            # Settings + default RSS list
│   ├── logger.py
│   ├── digest_runner.py     # Orchestrates the pipeline
│   ├── news/
│   │   ├── fetcher.py
│   │   ├── parser.py
│   │   ├── deduplicator.py
│   │   ├── ranker.py
│   │   └── summarizer.py
│   ├── telegram/
│   │   ├── bot.py
│   │   └── formatter.py
│   ├── scheduler/
│   │   └── jobs.py
│   └── utils/
│       ├── time_utils.py
│       └── retry.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## Quick start (local)

1. **Create a virtualenv and install dependencies**

   ```bash
   cd ai-news-telegram-bot
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Fill in at least:

   - `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)  
   - `TELEGRAM_CHAT_ID` — where scheduled digests go (see below)  
   - `OPENAI_API_KEY` — from [OpenAI](https://platform.openai.com/)  
   - `DIGEST_HOUR`, `DIGEST_MINUTE`, `TIMEZONE` — when the daily job runs  

3. **Run the bot (polling + daily schedule)**

   ```bash
   python -m app.main
   ```

4. **Send one digest immediately (uses `TELEGRAM_CHAT_ID`)**

   ```bash
   python -m app.main --once
   ```

5. **Run tests**

   ```bash
   pytest
   ```

## Telegram commands

| Command    | Description                                      |
|-----------|---------------------------------------------------|
| `/start`  | Short help                                        |
| `/send`   | Build today’s digest and send it **to this chat** |
| `/health` | Calls `getMe` to verify the token                 |
| `/sources`| Lists configured RSS feed URLs                    |

**Note:** The **scheduled** job always sends to `TELEGRAM_CHAT_ID`. `/send` sends to the chat where you issued the command (handy for DMs).

## How to get your Telegram chat ID

1. Start a chat with your bot (after creating it with BotFather).  
2. Send any message.  
3. Open:

   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`

4. Find `"chat":{"id": ... }` — that number (may be negative for groups) is your `TELEGRAM_CHAT_ID`.

For groups, add the bot, send a message, and read `getUpdates` again.

## Scheduling the daily digest

- **When running `python -m app.main`**, a **JobQueue** job is registered at  
  `DIGEST_HOUR`:`DIGEST_MINUTE` in `TIMEZONE` (IANA name, e.g. `America/New_York`, `Europe/Berlin`, `UTC`).
- The process must stay **running** (your laptop, a VPS, or a PaaS worker).
- **Alternatives for production:** GitHub Actions cron calling `python -m app.main --once`, or systemd timer, or Railway/Render **worker** that only runs the scheduler.

## Always-on hosting (no local machine)

The default mode uses **Telegram polling** and an in-process scheduler, so you need a **long-running worker**, not a “web service” that only starts on HTTP requests.

### Option A — Docker on a PaaS (simplest for many users)

1. Push this repo to GitHub (or connect the folder) on a host that runs **containers** or **background workers**.
2. Set the same variables as in `.env` in the host’s **environment / secrets** UI (see [Environment variables](#environment-variables) below). Do **not** rely on copying `.env` into the image; inject secrets at runtime.
3. Start command (if the platform asks for one): `python -m app.main`  
   The included `Dockerfile` already uses that as `CMD`.

**Examples:**

| Platform | What to create |
|----------|----------------|
| **[Railway](https://railway.app/)** | New project → deploy from repo → use Dockerfile; add variables under *Variables*. |
| **[Render](https://render.com/)** | **Background Worker** (not “Web Service”) → build from Dockerfile; set env vars. |
| **[Fly.io](https://fly.io/)** | `fly launch` with the Dockerfile; set secrets with `fly secrets set`. |

Use a **worker / private service** product name on your provider; if you only deploy a generic HTTP app, the process may be scaled to zero or not suit polling.

### Option B — VPS + systemd

On any Linux VPS, install Python 3.12+, clone the repo, create a virtualenv, install `requirements.txt`, put secrets in `/etc/ai-news-bot.env`, then use a `systemd` `Type=simple` service that runs `python -m app.main` and restarts on failure.

### Option C — Cron only (no always-on bot)

If you only need the **daily digest** and not live `/start` or `/send` in Telegram, you can run **`python -m app.main --once`** on a schedule (e.g. GitHub Actions `schedule`, or a cron job). Live commands will not work between runs.

## Configuring RSS feeds

Default feeds are defined in `app/config.py` (`DEFAULT_RSS_FEEDS`). Override with env:

```bash
# JSON array
NEWS_RSS_FEEDS='["https://techcrunch.com/category/artificial-intelligence/feed/","https://openai.com/blog/rss.xml"]'
```

Or comma-separated URLs (no JSON):

```bash
NEWS_RSS_FEEDS="https://example.com/feed.xml,https://another.com/rss"
```

If `NEWS_RSS_FEEDS` is empty, defaults apply.

### Example feed pack (AI / tech)

```json
[
  "https://techcrunch.com/category/artificial-intelligence/feed/",
  "https://venturebeat.com/category/ai/feed/",
  "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
  "https://openai.com/blog/rss.xml",
  "https://www.artificialintelligence-news.com/feed/",
  "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
]
```

Feeds change over time; if one 404s, it is skipped and logged.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | yes | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | yes | Target chat for scheduled + `--once` |
| `OPENAI_API_KEY` | yes | OpenAI API key |
| `OPENAI_MODEL` | no | Default `gpt-4o-mini` |
| `DIGEST_HOUR` | no | 0–23, default `8` |
| `DIGEST_MINUTE` | no | 0–59, default `0` |
| `TIMEZONE` | no | Default `UTC` |
| `NEWS_RSS_FEEDS` | no | JSON array or comma-separated URLs |
| `LOOKBACK_HOURS` | no | Default `36` |
| `MAX_ITEMS_IN_DIGEST` | no | Default `8` (cap 15) |
| `MAX_CANDIDATES_FOR_OPENAI` | no | Default `35` |
| `HTTP_TIMEOUT_SECONDS` | no | Default `20` |
| `LOG_LEVEL` | no | Default `INFO` |

## Production improvements (next steps)

- **Persistence:** store last-run watermark per feed to avoid reprocessing and to survive restarts.  
- **Rate limits:** backoff per domain; cache `ETag` / `Last-Modified`.  
- **Stronger dedupe:** embeddings or SimHash across title+snippet.  
- **Observability:** structured logging, Sentry, health endpoint if you add a small web process.  
- **Secrets:** use your host’s secret manager; never commit `.env`.  
- **Telegram limits:** refine HTML chunking so tags are never split mid-story.  
- **Content extraction:** for feeds with poor snippets, fetch `readability`/`trafilatura` on the article URL (cost + latency tradeoff).  
- **Tests:** VCR or mocked HTTP for fetcher integration tests.

## License

Use and modify freely for your own setup.
