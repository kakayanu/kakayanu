import pytest

from trading_agent.brokers.base import Account, Position
from trading_agent.risk.manager import RiskLimits, RiskManager, RiskViolation


def make_account(equity=10_000.0):
    return Account(equity=equity, cash=equity, buying_power=equity)


def test_order_within_limits_passes():
    rm = RiskManager(RiskLimits(max_position_pct=0.5, max_order_notional=1000))
    rm.validate_order("AAPL", 1, "buy", price=100, account=make_account(), positions=[])


def test_order_exceeding_notional_rejected():
    rm = RiskManager(RiskLimits(max_order_notional=100))
    with pytest.raises(RiskViolation):
        rm.validate_order("AAPL", 5, "buy", price=100, account=make_account(), positions=[])


def test_order_exceeding_position_pct_rejected():
    rm = RiskManager(RiskLimits(max_position_pct=0.05, max_order_notional=10_000))
    with pytest.raises(RiskViolation):
        rm.validate_order("AAPL", 10, "buy", price=100, account=make_account(equity=10_000), positions=[])


def test_symbol_not_allowed_rejected():
    rm = RiskManager(RiskLimits(allowed_symbols={"AAPL"}))
    with pytest.raises(RiskViolation):
        rm.validate_order("TSLA", 1, "buy", price=100, account=make_account(), positions=[])


def test_daily_loss_halts_trading():
    rm = RiskManager(RiskLimits(max_daily_loss_pct=0.05))
    rm.start_of_day(make_account(equity=10_000))
    with pytest.raises(RiskViolation):
        rm.validate_order("AAPL", 1, "buy", price=100, account=make_account(equity=9_000), positions=[])


def test_max_open_positions_rejected():
    rm = RiskManager(RiskLimits(max_open_positions=1, max_position_pct=1.0, max_order_notional=10_000))
    existing = [Position(symbol="MSFT", qty=1, avg_entry_price=100, market_value=100, unrealized_pl=0)]
    with pytest.raises(RiskViolation):
        rm.validate_order("AAPL", 1, "buy", price=100, account=make_account(), positions=existing)


def test_sell_ignores_position_pct_limit():
    rm = RiskManager(RiskLimits(max_position_pct=0.01, max_order_notional=10_000))
    existing = [Position(symbol="AAPL", qty=5, avg_entry_price=100, market_value=500, unrealized_pl=0)]
    rm.validate_order("AAPL", 5, "sell", price=100, account=make_account(), positions=existing)
