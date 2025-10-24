import re
from telegram import Update
from telegram.ext import ContextTypes
from .config import TELEGRAM_CHANNEL_ID

# Robustes Parsing für deine Screenshot-Formatierung (mit Emojis/Zeilenumbrüchen)
PAIR_RE = r'([A-Z0-9]+/[A-Z0-9]+)'
DIR_RE  = r'\b(LONG|SHORT)\b'
NUM_RE  = r'([-+]?\d*\.?\d+(?:e[-+]?\d+)?)'   # erlaubt 1.455e-05 etc.

def parse_signal(text: str):
    if not text:
        return None

    # Handelspaar
    m_pair = re.search(PAIR_RE, text, re.IGNORECASE)
    m_dir  = re.search(DIR_RE, text, re.IGNORECASE)

    # Entry / TP / SL (verschiedene Schreibweisen & Emojis)
    m_entry = re.search(r'Entry[:\s]*' + NUM_RE, text, re.IGNORECASE)
    m_tp    = re.search(r'TP[:\s]*'    + NUM_RE, text, re.IGNORECASE)
    m_sl    = re.search(r'SL[:\s]*'    + NUM_RE, text, re.IGNORECASE)

    if not (m_pair and m_dir and m_entry):
        return None

    pair = m_pair.group(1).upper()
    direction = m_dir.group(1).upper()
    entry = float(m_entry.group(1))
    tp = float(m_tp.group(1)) if m_tp else None
    sl = float(m_sl.group(1)) if m_sl else None

    return {"pair": pair, "direction": direction, "entry": entry, "tp": tp, "sl": sl}

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Nur Nachrichten aus DEINEM Kanal verarbeiten
    post = update.channel_post
    if not post or str(post.chat_id) != str(TELEGRAM_CHANNEL_ID):
        return

    text = post.text or post.caption or ""
    sig = parse_signal(text)
    if not sig:
        return

    # Trade ausführen
    result = await context.application.trade_executor.execute_trade(
        sig["pair"], sig["direction"], sig["entry"], sig["tp"], sig["sl"]
    )

    # Kurz quittieren (optional)
    try:
        msg = (
            f"✅ Signal verarbeitet: {sig['pair']} {sig['direction']}\n"
            f"Entry: {sig['entry']}"
            + (f" | TP: {sig['tp']}" if sig['tp'] else "")
            + (f" | SL: {sig['sl']}" if sig['sl'] else "")
            + (" | DRY-RUN" if result.get("dry_run") else "")
        )
        await post.reply_text(msg)
    except Exception:
        pass
