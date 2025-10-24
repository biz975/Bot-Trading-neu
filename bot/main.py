import asyncio
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from .telegram_listener import handle_channel_post
from .trade_executor import TradeExecutor
from .config import TELEGRAM_BOT_TOKEN

async def _startup(app):
    # Executor an Application hängen, damit Handler darauf zugreifen können
    app.trade_executor = TradeExecutor()

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))
    application.post_init = _startup
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
