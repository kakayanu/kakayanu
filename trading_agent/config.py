import os

from dotenv import load_dotenv

from .risk.manager import RiskLimits

load_dotenv()


def load_risk_limits() -> RiskLimits:
    allowed = os.environ.get("ALLOWED_SYMBOLS")
    return RiskLimits(
        max_position_pct=float(os.environ.get("MAX_POSITION_PCT", 0.10)),
        max_order_notional=float(os.environ.get("MAX_ORDER_NOTIONAL", 5000)),
        max_daily_loss_pct=float(os.environ.get("MAX_DAILY_LOSS_PCT", 0.03)),
        max_open_positions=int(os.environ.get("MAX_OPEN_POSITIONS", 10)),
        allowed_symbols=set(allowed.split(",")) if allowed else None,
    )
