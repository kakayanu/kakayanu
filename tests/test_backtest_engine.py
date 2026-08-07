from datetime import datetime, timedelta

from trading_agent.backtest.engine import moving_average_crossover, run_backtest
from trading_agent.brokers.base import Bar


def make_bars(closes):
    start = datetime(2024, 1, 1)
    return [
        Bar(timestamp=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1000)
        for i, c in enumerate(closes)
    ]


def test_backtest_runs_and_returns_result():
    closes = [100] * 20 + [101, 103, 106, 110, 115, 120, 118, 116, 112, 108]
    bars = make_bars(closes)
    strategy = moving_average_crossover(fast=3, slow=10)
    result = run_backtest("TEST", bars, strategy, starting_cash=10_000, order_qty=1, warmup=10)
    assert result.starting_equity == 10_000
    assert isinstance(result.final_equity, float)


def test_backtest_no_trades_when_flat_prices():
    closes = [100] * 30
    bars = make_bars(closes)
    strategy = moving_average_crossover(fast=3, slow=10)
    result = run_backtest("TEST", bars, strategy, starting_cash=10_000, warmup=10)
    assert result.trades == []
    assert result.final_equity == 10_000


def test_backtest_buys_on_golden_cross():
    closes = [100] * 15 + [102, 105, 109, 114, 120]
    bars = make_bars(closes)
    strategy = moving_average_crossover(fast=3, slow=10)
    result = run_backtest("TEST", bars, strategy, starting_cash=10_000, order_qty=1, warmup=10)
    assert any(t["side"] == "buy" for t in result.trades)
