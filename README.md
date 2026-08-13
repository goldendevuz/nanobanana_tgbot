# Nano Banana Telegram Bot

Telegram bot that generates images with the [Kie.ai](https://kie.ai) `google/nano-banana` model,
backed by a Django project with an [Unfold](https://unfoldadmin.com) admin dashboard.

- **aiogram 3** — long-polling bot, run as a Django management command
- **Trilingual** — Uzbek (default), Russian and English, picked per user
- **Django ORM** — Telegram users and generation jobs are persisted, so pending jobs survive a restart
- **django-unfold** — dashboard with KPIs, a 14-day chart, image previews and per-user access control
- **python-decouple** — all configuration comes from `.env`
- **WhiteNoise** — static files served straight from the app process
- **dj-database-url** — SQLite by default, PostgreSQL via `DATABASE_URL`

## Layout

```
core/            Django project (settings, urls, dashboard callback)
bot/
  models.py      TelegramUser, GenerationTask
  admin.py       Unfold admin
  i18n.py        uz / ru / en string catalogue
  services/
    image_service.py   Kie.ai API client
    telegram_bot.py    aiogram handlers + result poller
  management/commands/runbot.py
templates/admin/index.html   Custom dashboard
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Copy the environment template and fill it in:

```bash
cp .env.example .env
```

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | Optional; defaults to local SQLite |
| `TELEGRAM_BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_USER_ID` | Your Telegram user id — always has access |
| `BOT_ALLOW_EVERYONE` | `True` to skip the allow-list entirely |
| `BOT_POLL_INTERVAL` | Seconds between Kie.ai status checks |
| `KIE_API_KEY` | Kie.ai API key |
| `KIE_MODEL` | Defaults to `google/nano-banana` |

Then migrate and create an admin account:

```bash
python manage.py migrate && python manage.py createsuperuser
```

## Run

Two processes — the web admin and the bot:

```bash
python manage.py runserver
```

```bash
python manage.py runbot
```

The admin lives at http://127.0.0.1:8000/admin/ (`/` redirects there).

## Languages

The bot speaks **Uzbek (default), Russian and English**. On first contact the language is
guessed from the Telegram client locale (`ru-RU` → Russian, anything unsupported →
Uzbek) and stored on the user. It can be changed any time with `/language` or the
**🌐** keyboard button, and staff can override it from the admin.

All copy lives in [`bot/i18n.py`](bot/i18n.py) as a plain dict — add a language by adding a
key to `TEXTS` and to `TelegramUser.Language`. Keyboard buttons are matched against every
language at once, so a user who switches mid-session never gets a dead button.

## Access control

Every Telegram account that messages the bot is recorded as a `TelegramUser`. Only
`ADMIN_USER_ID`, users flagged **Allowed** in the admin, or everyone when
`BOT_ALLOW_EVERYONE=True` may generate images. Use the *Grant access* / *Block* bulk
actions on the Telegram users list.

## Production

```bash
python manage.py collectstatic --noinput
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

Run `python manage.py runbot` as a separate long-running process (systemd unit, container,
or `Procfile` worker).
