# Environment Variables

<!-- AUTO-GENERATED -->

All environment variables are loaded from `.env` file in the project root. See `.env.example` for the template.

**Last Updated:** 2024-04-03

## Quick Setup

```bash
cp .env.example .env
# Edit .env with your values
```

## Binance Exchange Credentials

### Live Trading

**`BINANCE_API_KEY`**
- **Required for:** Live mode only
- **Type:** String
- **Description:** Your Binance API public key for live trading
- **Where to get:** [Binance API Management](https://www.binance.com/en/account/api-management)
- **Security:** Never commit to version control; store securely
- **Example:** `vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MutiDF3blmRsY0K6K7K7StewQYAAXXccNwrZr45IqM9MRcTO3smznEsziJjUXvwi`
- **Default:** Empty (live mode disabled)

**`BINANCE_API_SECRET`**
- **Required for:** Live mode only
- **Type:** String
- **Description:** Your Binance API secret key for live trading
- **Where to get:** [Binance API Management](https://www.binance.com/en/account/api-management)
- **Security:** Never commit to version control; store in secret manager
- **Example:** `NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7h5hhikYa`
- **Default:** Empty (live mode disabled)

### Binance Testnet

**`BINANCE_TESTNET_API_KEY`**
- **Required for:** Testnet mode
- **Type:** String
- **Description:** Binance Testnet API public key for risk-free testing
- **Where to get:** [Binance Testnet Registration](https://testnet.binance.vision/)
- **Security:** Can be safely committed (testnet only, no real funds)
- **Example:** `testnet-api-key-12345`
- **Default:** Empty (testnet mode disabled)

**`BINANCE_TESTNET_API_SECRET`**
- **Required for:** Testnet mode
- **Type:** String
- **Description:** Binance Testnet API secret key
- **Where to get:** [Binance Testnet Registration](https://testnet.binance.vision/)
- **Security:** Can be safely committed (testnet only, no real funds)
- **Example:** `testnet-api-secret-12345`
- **Default:** Empty (testnet mode disabled)

## Notifications (Optional)

### Telegram Alerts

**`TELEGRAM_BOT_TOKEN`**
- **Required for:** Telegram notifications
- **Type:** String
- **Description:** Bot token for Telegram notifications on trades/alerts
- **Where to get:** [Create bot with BotFather](https://core.telegram.org/bots#botfather)
- **Format:** `1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh`
- **Security:** Keep confidential (controls bot API access)
- **Default:** Empty (Telegram notifications disabled)
- **Example:** `5397621097:AAHqc8Z9fJ2CX9K0c8m_I1h3Jk5L2M9nQpO`

**`TELEGRAM_CHAT_ID`**
- **Required for:** Telegram notifications (if token is set)
- **Type:** Integer or String
- **Description:** Telegram chat/channel ID to receive trade notifications
- **Where to get:** Message [@userinfobot](https://t.me/userinfobot) in Telegram to get your chat ID
- **Format:** `-1001234567890` (group/channel) or `1234567890` (private)
- **Default:** Empty
- **Example:** `-1001234567890` (for a channel) or `987654321` (for a direct chat)

## Dashboard Authentication (Optional)

**`DASHBOARD_API_KEY`**
- **Required for:** Dashboard API authentication
- **Type:** String (URL-safe base64)
- **Description:** API key for Dashboard HTTP requests authentication
- **When needed:** Set this to enable authentication on the dashboard API
- **When to skip:** Leave empty for local development (authentication disabled)
- **Security:** In production, always set to a strong random value
- **Generate:** `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **Example:** `xH7mK_qL9nPq2rJv8sW5xYz3aB4cD6eF9gH2jK5mL8`
- **Default:** Empty (authentication disabled in development)

## Logging Configuration (Environment-based)

**`LOG_FORMAT`** (Optional)
- **Type:** String
- **Values:** `json` or empty/other (default human-readable)
- **Description:** Output format for logs
- **Default:** Human-readable console output
- **Use case:**
  - Leave empty or unset for local development (pretty console logs)
  - Set to `json` for production/Docker (structured logging for aggregators)
- **Example:**
  ```bash
  # Development
  # LOG_FORMAT not set or empty

  # Production
  LOG_FORMAT=json
  ```

## Complete .env.example Template

```bash
# ==============================================================
# Binance Live Trading (NOT NEEDED for paper mode)
# ==============================================================
BINANCE_API_KEY=
BINANCE_API_SECRET=

# ==============================================================
# Binance Testnet (free, but trades on testnet only)
# ==============================================================
BINANCE_TESTNET_API_KEY=
BINANCE_TESTNET_API_SECRET=

# ==============================================================
# Telegram Notifications (optional)
# ==============================================================
# Create bot with BotFather: https://t.me/botfather
TELEGRAM_BOT_TOKEN=
# Get your chat ID from @userinfobot
TELEGRAM_CHAT_ID=

# ==============================================================
# Dashboard Security (optional, development only by default)
# ==============================================================
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
# Leave empty to disable authentication (development)
DASHBOARD_API_KEY=
```

## Usage in Code

### Reading Environment Variables

All environment variables are loaded via `src/utils/config.py`:

```python
from src.utils.config import load_env

env = load_env()

# Access variables
api_key = env.binance_api_key
api_secret = env.binance_api_secret
telegram_token = env.telegram_bot_token
dashboard_key = env.dashboard_api_key
```

### Validation Rules

- **API Keys:** Must not be empty when trading mode is `testnet` or `live`
- **Telegram:** Both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` required for notifications
- **Dashboard Key:** Optional; if empty, authentication is disabled (development only)

### Loading Process

1. `.env` file is loaded from project root (via `python-dotenv`)
2. Missing variables default to empty strings
3. Validation occurs when selecting trading mode

## Security Best Practices

### DO ✅

- Keep `.env` file in `.gitignore` (never commit)
- Use environment variables for all secrets
- Rotate API keys regularly
- Use testnet API keys for testing
- Store live keys in a secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- Use IP whitelisting on Binance API keys

### DON'T ❌

- Hardcode API keys in code
- Commit `.env` to version control
- Share API keys via chat/email
- Log API keys (check structlog filters)
- Use the same API key across multiple machines
- Store keys in config files (use environment variables instead)

## Setup by Trading Mode

### Paper Mode (Simulation - No Real Capital)

```bash
# .env
# Leave all API keys empty
# No configuration needed — bot trades with simulated balance
```

Run:
```bash
trade-bot run
```

### Testnet Mode (Free, Test-only Funds)

```bash
# .env
BINANCE_TESTNET_API_KEY=your-testnet-api-key
BINANCE_TESTNET_API_SECRET=your-testnet-api-secret

# config/default.yaml
mode: "testnet"
```

Run:
```bash
trade-bot --config config/default.yaml run
```

### Live Mode (Real Capital ⚠️)

```bash
# .env
BINANCE_API_KEY=your-live-api-key
BINANCE_API_SECRET=your-live-api-secret

# config/default.yaml
mode: "live"
```

**WARNING:** Only use live mode after thorough testing on paper and testnet!

Run:
```bash
trade-bot --config config/live.yaml run
```

## Troubleshooting

### "API Key Error" on startup

**Problem:** Bot can't authenticate with exchange
- **Check:** Is `BINANCE_API_KEY` and `BINANCE_API_SECRET` set in `.env`?
- **Check:** Are credentials correct? (Copy-paste errors are common)
- **Check:** Is the trading mode in config matching the credentials you provided?
  - Use `BINANCE_API_KEY`/`BINANCE_API_SECRET` for live mode
  - Use `BINANCE_TESTNET_API_KEY`/`BINANCE_TESTNET_API_SECRET` for testnet
  - Don't set any for paper mode

### "Dashboard API authentication failed"

**Problem:** Getting 401 Unauthorized on dashboard API calls
- **Check:** Is `DASHBOARD_API_KEY` set in `.env`?
- **Fix:** Either set the key and include it in requests, or leave empty for development

### Environment variables not being loaded

**Problem:** `.env` file exists but variables are empty
- **Check:** Is `.env` in the project root? (Not in a subdirectory)
- **Check:** Did you restart the bot after creating/editing `.env`?
- **Fix:** Verify `.env` format (no extra spaces, key=value on each line)

### Can't generate testnet API keys

1. Go to [Binance Testnet](https://testnet.binance.vision/)
2. Click "Connect with Github" or create account
3. In API Management, click "Create API" → "System-generated"
4. Copy the API Key and Secret to `.env`

## Related Files

- `.env.example` — Template for environment variables
- `src/utils/config.py` — Loading and validation logic
- `config/default.yaml` — Trading strategy configuration

<!-- END AUTO-GENERATED -->
