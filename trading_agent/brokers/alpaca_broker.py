import os
from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide as AlpacaOrderSide
from alpaca.trading.enums import TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .base import Account, Bar, Broker, Order, OrderSide, Position

_TIMEFRAME_MAP = {"1Min": TimeFrame.Minute, "1Hour": TimeFrame.Hour, "1Day": TimeFrame.Day}


class AlpacaBroker(Broker):
    """US equities via Alpaca. Defaults to the paper-trading endpoint."""

    name = "alpaca"

    def __init__(self, api_key: str | None = None, secret_key: str | None = None, paper: bool = True):
        api_key = api_key or os.environ["ALPACA_API_KEY"]
        secret_key = secret_key or os.environ["ALPACA_SECRET_KEY"]
        self.trading = TradingClient(api_key, secret_key, paper=paper)
        self.data = StockHistoricalDataClient(api_key, secret_key)

    def get_account(self) -> Account:
        a = self.trading.get_account()
        return Account(equity=float(a.equity), cash=float(a.cash), buying_power=float(a.buying_power))

    def get_positions(self) -> list[Position]:
        return [
            Position(
                symbol=p.symbol,
                qty=float(p.qty),
                avg_entry_price=float(p.avg_entry_price),
                market_value=float(p.market_value),
                unrealized_pl=float(p.unrealized_pl),
            )
            for p in self.trading.get_all_positions()
        ]

    def get_bars(self, symbol: str, timeframe: str, limit: int) -> list[Bar]:
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=_TIMEFRAME_MAP.get(timeframe, TimeFrame.Day),
            start=datetime.utcnow() - timedelta(days=limit * 2 + 5),
            limit=limit,
        )
        bars = self.data.get_stock_bars(req).data[symbol]
        return [
            Bar(timestamp=b.timestamp, open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume)
            for b in bars[-limit:]
        ]

    def get_quote(self, symbol: str) -> float:
        req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = self.data.get_stock_latest_quote(req)[symbol]
        return (quote.bid_price + quote.ask_price) / 2

    def place_order(self, symbol: str, qty: float, side: OrderSide) -> Order:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=AlpacaOrderSide.BUY if side == "buy" else AlpacaOrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        o = self.trading.submit_order(req)
        return Order(id=str(o.id), symbol=symbol, qty=qty, side=side, status=str(o.status))

    def get_open_orders(self) -> list[Order]:
        return [
            Order(
                id=str(o.id),
                symbol=o.symbol,
                qty=float(o.qty),
                side="buy" if o.side.value == "buy" else "sell",
                status=str(o.status),
            )
            for o in self.trading.get_orders()
        ]

    def cancel_all_orders(self) -> None:
        self.trading.cancel_orders()
