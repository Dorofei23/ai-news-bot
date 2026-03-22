## Learned User Preferences

- Digest should emphasize AI applied to UI engineering (React, React Native, web), with a small number of high-signal pure frontend items when they materially affect daily work.
- Also wants notable developer-tooling releases and vendor AI updates (e.g. major labs and tools devs actually use), not only generic news headlines.
- Prefers running the bot on always-on cloud hosting rather than keeping it running on a personal machine.
- Often discusses this project in Russian; keep explanations and operational help accessible in Russian when the user writes in Russian.

## Learned Workspace Facts

- This repo is a Python Telegram bot: configurable RSS feeds, dedupe and ranking, OpenAI for selection/summaries, scheduled and manual digest delivery.
- Entrypoints: `python -m app.main` for polling plus the daily job; `python -m app.main --once` for a single digest send without a long-lived process (suitable for cron or CI).
- The `Dockerfile` starts `python -m app.main`; production requires environment variables (e.g. from the host or secrets manager), not baking secrets into the image.
- If `NEWS_RSS_FEEDS` is set in `.env`, it fully replaces the default feed list from code—defaults are not merged in.
- `OPENAI_API_KEY` must be a real OpenAI API key; editor subscriptions such as Cursor or GitHub Copilot are not drop-in replacements for that variable in this project.
