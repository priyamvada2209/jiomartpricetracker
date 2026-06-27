# JioMart Price Tracker

Telegram bot for tracking JioMart product prices and sending daily summaries to multiple users.

## What It Does

- Fetches price data from the JioMart API for the products listed in `products.json`
- Stores every fetch in a SQL database as price history
- Exposes a Telegram bot with webhook-based updates
- Lets any Telegram user:
  - `/start` to register and enable notifications
  - `/today` to fetch fresh prices immediately
  - `/prices` to view the latest stored prices from the database
  - `/help` to see available commands
  - `/stop` to disable notifications
- Runs a daily scheduler that fetches prices once and sends the same summary to every active Telegram user

## Architecture

- `main.py` starts the Flask app
- `jiomart_price_tracker/web.py` creates the Flask application and webhook endpoints
- `jiomart_price_tracker/telegram_runtime.py` manages the Telegram bot and command handlers
- `jiomart_price_tracker/scheduler.py` runs the daily background job
- `jiomart_price_tracker/fetcher.py` talks to the JioMart API
- `jiomart_price_tracker/database.py` sets up SQLAlchemy and database sessions
- `jiomart_price_tracker/models.py` defines the ORM tables

## Database Tables

### `price_history`

Stores one row per product per fetch.

- `id`
- `product_slug`
- `product_name`
- `price`
- `fetched_at`

### `telegram_users`

Stores Telegram users who have interacted with the bot.

- `id`
- `telegram_chat_id`
- `telegram_user_id`
- `username`
- `first_name`
- `created_at`
- `last_seen`
- `notifications_enabled`

## Requirements

- Python 3.13+
- MySQL or SQLite
- A Telegram bot token from BotFather
- A public HTTPS webhook URL

## Environment Variables

Create a `.env` file from `.env.example` and fill in:

```env
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=https://your-public-domain/webhook
DATABASE_URL=sqlite:///prices.db
JIOMART_API_URL=https://your-jiomart-api-url
JIOMART_AUTHORIZATION=your_jiomart_authorization_header
LATITUDE=0.000000
LONGITUDE=0.000000
POLYGON_ID=your_polygon_id
CITY=Your City
PINCODE=000000
STATE=Your State
COUNTRY=Your Country
COUNTRY_ISO_CODE=IN
```

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from `.env.example`.
4. Start a public tunnel for local webhook testing with `ngrok` or `cloudflared`.
5. Set `WEBHOOK_URL` to your tunnel URL plus `/webhook`.
6. Run the app:
   ```bash
   python main.py
   ```

## How to Use the Bot

1. Open the bot in Telegram.
2. Send `/start`.
3. Use the commands:
   - `/today` for a live fetch
   - `/prices` for the latest stored snapshot
   - `/stop` to disable notifications
   - `/help` for the command list

## Scheduler

- The daily APScheduler job runs at **6:00 AM IST**
- On each run it:
  1. fetches JioMart prices once
  2. stores them in `price_history`
  3. builds a summary
  4. loads all users with `notifications_enabled = true`
  5. sends the summary to each active user

## Railway Deployment

- Deploy the app as a long-running web service
- Use a production WSGI server such as `gunicorn`
- Set all environment variables in Railway
- Point `WEBHOOK_URL` at the Railway public URL ending in `/webhook`
- Keep the app running continuously so Telegram can deliver updates

## Notes

- `telegram_users` is created automatically on startup if it does not exist
- `/start` upserts the user and re-enables notifications
- `/prices` reads from the database only and does not call JioMart
- Product history is shared across all users; it is not stored per user

