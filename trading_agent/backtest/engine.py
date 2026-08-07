from dataclasses import dataclass, field
from typing import Callable

from ..brokers.base import Bar

Strategy = Callable[[str, list[Bar]], str]  # returns "buy", "sell", or "hold"


@dataclass
class BacktestResult:
    trades: list[dict] = field(default_factory=list)
    starting_equity: float = 0.0
    final_equity: float = 0.0

    @property
    def return_pct(self) -> float:
        if self.starting_equity == 0:
            return 0.0
        return (self.final_equity - self.starting_equity) / self.starting_equity


def run_backtest(
    symbol: str,
    bars: list[Bar],
    strategy: Strategy,
    starting_cash: float = 10_000.0,
    order_qty: float = 1.0,
    warmup: int = 5,
) -> BacktestResult:
    """Replay historical bars through a deterministic strategy function.

    This is for validating rule-based strategies cheaply; running the live Claude
    agent bar-by-bar over history is possible but costs an API call per step.
    """
    cash = starting_cash
    position_qty = 0.0
    trades: list[dict] = []

    for i in range(warmup, len(bars)):
        window = bars[: i + 1]
        price = bars[i].close
        action = strategy(symbol, window)

        if action == "buy" and cash >= price * order_qty:
            cash -= price * order_qty
            position_qty += order_qty
            trades.append({"timestamp": bars[i].timestamp.isoformat(), "side": "buy", "price": price, "qty": order_qty})
        elif action == "sell" and position_qty >= order_qty:
            cash += price * order_qty
            position_qty -= order_qty
            trades.append({"timestamp": bars[i].timestamp.isoformat(), "side": "sell", "price": price, "qty": order_qty})

    final_price = bars[-1].close if bars else 0.0
    final_equity = cash + position_qty * final_price

    return BacktestResult(trades=trades, starting_equity=starting_cash, final_equity=final_equity)


def moving_average_crossover(fast: int = 5, slow: int = 20) -> Strategy:
    def strategy(symbol: str, bars: list[Bar]) -> str:
        if len(bars) < slow + 1:
            return "hold"
        closes = [b.close for b in bars]
        fast_avg = sum(closes[-fast:]) / fast
        slow_avg = sum(closes[-slow:]) / slow
        prev_fast_avg = sum(closes[-fast - 1 : -1]) / fast
        prev_slow_avg = sum(closes[-slow - 1 : -1]) / slow
        if prev_fast_avg <= prev_slow_avg and fast_avg > slow_avg:
            return "buy"
        if prev_fast_avg >= prev_slow_avg and fast_avg < slow_avg:
            return "sell"
        return "hold"

    return strategy
