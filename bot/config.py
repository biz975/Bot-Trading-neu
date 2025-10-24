import os

# Telegram
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]          # z.B. 12345:ABC...
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]         # z.B. -1001234567890

# MEXC via CCXT (USDT-Margined SWAP/Futures)
MEXC_API_KEY = os.environ["MEXC_API_KEY"]
MEXC_API_SECRET = os.environ["MEXC_API_SECRET"]

# Trade-Defaults
MARGIN_USDT = float(os.environ.get("MARGIN_USDT", "10"))        # 10 USDT pro Trade
LEVERAGE = int(os.environ.get("LEVERAGE", "25"))                # 25x
TAKE_PROFIT_PCT = float(os.environ.get("TAKE_PROFIT_PCT", "0.15"))  # +15%
STOP_LOSS_PCT = float(os.environ.get("STOP_LOSS_PCT", "0.40"))      # -40%

# Sicherheit
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"                 # 1=keine Orders senden (Test)
