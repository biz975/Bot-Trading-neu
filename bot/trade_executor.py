import math
import ccxt
from .config import (
    MEXC_API_KEY, MEXC_API_SECRET, MARGIN_USDT, LEVERAGE,
    TAKE_PROFIT_PCT, STOP_LOSS_PCT, DRY_RUN
)

class TradeExecutor:
    """
    Ausführung über CCXT auf MEXC (USDT-Margined SWAP).
    - Öffnet Market-Position (isolated, hedged-fähig)
    - Setzt Hebel
    - Platziert TP/SL als getrennte reduceOnly Trigger-Orders (Best-Effort)
    """

    def __init__(self):
        self.ex = ccxt.mexc({
            "apiKey": MEXC_API_KEY,
            "secret": MEXC_API_SECRET,
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",      # <-- wichtig: Futures/Perps
            }
        })
        # Position-Modus: hedged (Long/Short getrennt), falls unterstützt
        try:
            self.ex.set_position_mode(True)   # True = hedged, False = one-way
        except Exception:
            pass

    def _to_mexc_symbol(self, pair: str) -> str:
        """
        Telegram nutzt 'FLOW/USDT' – CCXT für MEXC-Swap erwartet 'FLOW/USDT:USDT'
        (Base/Quote:Margin-Asset). Für USDT-Perps ist das ':USDT'.
        """
        pair = pair.upper().replace(" ", "")
        if ":USDT" in pair:
            return pair
        if "/USDT" in pair:
            return pair + ":USDT"
        # Fallback
        return pair + ":USDT"

    async def execute_trade(self, pair: str, direction: str, entry: float,
                            tp: float | None, sl: float | None) -> dict:
        sym = self._to_mexc_symbol(pair)
        side = "buy" if direction.upper() == "LONG" else "sell"

        # Notional = 10 USDT * 25x = 250 USDT => amount = notional / price
        notional = MARGIN_USDT * LEVERAGE
        amount = notional / max(entry, 1e-12)

        # MEXC Tick-Rundungen per CCXT-Marktinfos
        market = await self.ex.load_markets()
        info = market[sym]
        amount = float(self.ex.amount_to_precision(sym, amount))

        # Hebel setzen (isolated)
        try:
            await self.ex.set_leverage(LEVERAGE, sym, params={"marginMode": "isolated"})
        except Exception:
            # Einige Märkte setzen leverage implizit – nicht kritisch
            pass

        result = {"opened": None, "tp": None, "sl": None, "dry_run": DRY_RUN}

        if DRY_RUN:
            result["opened"] = {
                "symbol": sym, "side": side, "amount": amount,
                "note": "DRY_RUN aktiv – keine Order gesendet"
            }
            return result

        # 1) Market-Order eröffnen
        order = await self.ex.create_order(
            sym, "market", side, amount,
            params={
                "marginMode": "isolated",
                "leverage": LEVERAGE,
                "reduceOnly": False,
            }
        )
        result["opened"] = order

        # Entry-Preis für Berechnung (falls kein TP/SL vorgegeben)
        exec_price = entry
        try:
            if order and order.get("price"):
                exec_price = float(order["price"])
            elif order and order.get("average"):
                exec_price = float(order["average"])
        except Exception:
            pass

        # 2) TP/SL berechnen (falls nicht im Signal vorgegeben)
        if tp is None:
            tp = exec_price * (1 + TAKE_PROFIT_PCT) if side == "buy" else exec_price * (1 - TAKE_PROFIT_PCT)
        if sl is None:
            sl = exec_price * (1 - STOP_LOSS_PCT) if side == "buy" else exec_price * (1 + STOP_LOSS_PCT)

        tp = float(self.ex.price_to_precision(sym, tp))
        sl = float(self.ex.price_to_precision(sym, sl))

        # reduceOnly-Menge (ganze Position)
        reduce_amount = amount

        # 3) Take-Profit Trigger-Order (reduceOnly)
        try:
            # Gegenrichtung schließen: bei Long -> sell, bei Short -> buy
            tp_side = "sell" if side == "buy" else "buy"
            tp_order = await self.ex.create_order(
                sym, "market", tp_side, reduce_amount,
                params={
                    "reduceOnly": True,
                    "triggerPrice": tp,           # CCXT unified param
                    "stopPrice": tp,              # für Exchanges mit 'stopPrice'
                    "type": "take_profit",        # wird bei vielen Börsen in Trigger-Order übersetzt
                }
            )
            result["tp"] = tp_order
        except Exception as e:
            result["tp"] = {"error": str(e), "intended_trigger": tp}

        # 4) Stop-Loss Trigger-Order (reduceOnly)
        try:
            sl_side = "sell" if side == "buy" else "buy"
            sl_order = await self.ex.create_order(
                sym, "market", sl_side, reduce_amount,
                params={
                    "reduceOnly": True,
                    "triggerPrice": sl,
                    "stopPrice": sl,
                    "type": "stop_loss",
                }
            )
            result["sl"] = sl_order
        except Exception as e:
            result["sl"] = {"error": str(e), "intended_trigger": sl}

        return result
