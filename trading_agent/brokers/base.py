from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

OrderSide = Literal["buy", "sell"]


@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    unrealized_pl: float


@dataclass
class Account:
    equity: float
    cash: float
    buying_power: float


@dataclass
class Order:
    id: str
    symbol: str
    qty: float
    side: OrderSide
    status: str
    filled_avg_price: Optional[float] = None


class Broker(ABC):
    """Broker-agnostic interface. Every adapter (Alpaca, ccxt, ...) implements this."""

    name: str

    @abstractmethod
    def get_account(self) -> Account: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, limit: int) -> list[Bar]: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> float: ...

    @abstractmethod
    def place_order(self, symbol: str, qty: float, side: OrderSide) -> Order: ...

    @abstractmethod
    def get_open_orders(self) -> list[Order]: ...

    @abstractmethod
    def cancel_all_orders(self) -> None: ...
