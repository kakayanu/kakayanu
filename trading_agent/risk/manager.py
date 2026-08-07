from dataclasses import dataclass

from ..brokers.base import Account, OrderSide, Position


@dataclass
class RiskLimits:
    max_position_pct: float = 0.10  # max % of equity in a single symbol
    max_order_notional: float = 5000.0  # hard cap per order, in quote currency
    max_daily_loss_pct: float = 0.03  # halt trading if equity drops this much from day start
    max_open_positions: int = 10
    allowed_symbols: set[str] | None = None  # None = no allowlist restriction


class RiskViolation(Exception):
    pass


class RiskManager:
    """Deterministic guardrails the agent cannot reason its way around.

    The LLM proposes trades; every proposal is validated here before it reaches
    the broker. Nothing in this class is influenced by model output.
    """

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self._starting_equity: float | None = None

    def start_of_day(self, account: Account) -> None:
        self._starting_equity = account.equity

    def check_daily_loss(self, account: Account) -> None:
        if self._starting_equity is None:
            self._starting_equity = account.equity
            return
        loss_pct = (self._starting_equity - account.equity) / self._starting_equity
        if loss_pct >= self.limits.max_daily_loss_pct:
            raise RiskViolation(
                f"Daily loss {loss_pct:.2%} exceeds limit {self.limits.max_daily_loss_pct:.2%}; trading halted."
            )

    def validate_order(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        price: float,
        account: Account,
        positions: list[Position],
    ) -> None:
        if self.limits.allowed_symbols is not None and symbol not in self.limits.allowed_symbols:
            raise RiskViolation(f"{symbol} is not in the allowed symbols list.")

        self.check_daily_loss(account)

        notional = qty * price
        if notional > self.limits.max_order_notional:
            raise RiskViolation(
                f"Order notional {notional:.2f} exceeds max_order_notional {self.limits.max_order_notional:.2f}."
            )

        if side == "buy":
            existing = next((p for p in positions if p.symbol == symbol), None)
            existing_value = existing.market_value if existing else 0.0
            position_pct = (existing_value + notional) / account.equity
            if position_pct > self.limits.max_position_pct:
                raise RiskViolation(
                    f"Resulting position in {symbol} would be {position_pct:.2%} of equity, "
                    f"exceeding max_position_pct {self.limits.max_position_pct:.2%}."
                )

            open_symbols = {p.symbol for p in positions}
            if symbol not in open_symbols and len(open_symbols) >= self.limits.max_open_positions:
                raise RiskViolation(f"Already at max_open_positions ({self.limits.max_open_positions}).")
