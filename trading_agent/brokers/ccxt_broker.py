import os
from datetime import datetime

import ccxt

from .base import Account, Bar, Broker, Order, OrderSide, Position

_TIMEFRAME_MAP = {"1Min": "1m", "1Hour": "1h", "1Day": "1d"}


class CCXTBroker(Broker):
    """Crypto via any ccxt-supported exchange. Defaults to sandbox/testnet mode."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
    ):
        self.name = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(
            {
                "apiKey": api_key or os.environ.get(f"{exchange_id.upper()}_API_KEY", ""),
                "secret": secret or os.environ.get(f"{exchange_id.upper()}_SECRET", ""),
                "enableRateLimit": True,
            }
        )
        if sandbox:
            self.exchange.set_sandbox_mode(True)

    def get_account(self) -> Account:
        bal = self.exchange.fetch_balance()
        total = bal.get("total", {})
        cash = float(total.get("USDT", total.get("USD", 0.0)) or 0.0)
        return Account(equity=cash, cash=cash, buying_power=cash)

    def get_positions(self) -> list[Position]:
        bal = self.exchange.fetch_balance()
        positions = []
        for asset, amount in bal.get("total", {}).items():
            if amount and amount > 0 and asset not in ("USDT", "USD"):
                positions.append(
                    Position(symbol=asset, qty=float(amount), avg_entry_price=0.0, market_value=0.0, unrealized_pl=0.0)
                )
        return positions

    def get_bars(self, symbol: str, timeframe: str, limit: int) -> list[Bar]:
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=_TIMEFRAME_MAP.get(timeframe, "1d"), limit=limit)
        return [
            Bar(timestamp=datetime.utcfromtimestamp(t / 1000), open=o, high=h, low=l, close=c, volume=v)
            for t, o, h, l, c, v in ohlcv
        ]

    def get_quote(self, symbol: str) -> float:
        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker["last"])

    def place_order(self, symbol: str, qty: float, side: OrderSide) -> Order:
        o = self.exchange.create_order(symbol, "market", side, qty)
        return Order(id=str(o["id"]), symbol=symbol, qty=qty, side=side, status=str(o.get("status", "unknown")))

    def get_open_orders(self) -> list[Order]:
        orders = self.exchange.fetch_open_orders()
        return [
            Order(id=str(o["id"]), symbol=o["symbol"], qty=float(o["amount"]), side=o["side"], status=o["status"])
            for o in orders
        ]

    def cancel_all_orders(self) -> None:
        for o in self.get_open_orders():
            self.exchange.cancel_order(o.id, o.symbol)
