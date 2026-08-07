from typing import Any

from ..brokers.base import Broker
from ..logging_utils import TradeLogger
from ..risk.manager import RiskManager, RiskViolation

TOOL_SCHEMAS = [
    {
        "name": "get_account_state",
        "description": "Get current account equity, cash, and buying power.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_positions",
        "description": "List all current open positions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_market_data",
        "description": "Get recent OHLCV bars for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": ["1Min", "1Hour", "1Day"], "default": "1Day"},
                "limit": {"type": "integer", "default": 30},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_quote",
        "description": "Get the latest price quote for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "place_order",
        "description": (
            "Submit a market order. This is validated against hard-coded risk limits (max position "
            "size, max order notional, daily loss halt) before execution; the order is rejected if it "
            "violates them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "qty": {"type": "number"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "reason": {"type": "string", "description": "Brief justification for this trade."},
            },
            "required": ["symbol", "qty", "side", "reason"],
        },
    },
]


class TradingToolkit:
    """Bridges the LLM's tool calls to the broker, with every order passing through the risk manager."""

    def __init__(self, broker: Broker, risk_manager: RiskManager, logger: TradeLogger):
        self.broker = broker
        self.risk_manager = risk_manager
        self.logger = logger

    def dispatch(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return {"error": f"Unknown tool {tool_name}"}
        try:
            return handler(**tool_input)
        except RiskViolation as e:
            self.logger.log_event("risk_rejected", {"tool": tool_name, "input": tool_input, "reason": str(e)})
            return {"error": f"Risk check failed: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_get_account_state(self) -> dict:
        a = self.broker.get_account()
        return {"equity": a.equity, "cash": a.cash, "buying_power": a.buying_power}

    def _tool_get_positions(self) -> dict:
        return {
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": p.qty,
                    "avg_entry_price": p.avg_entry_price,
                    "market_value": p.market_value,
                    "unrealized_pl": p.unrealized_pl,
                }
                for p in self.broker.get_positions()
            ]
        }

    def _tool_get_market_data(self, symbol: str, timeframe: str = "1Day", limit: int = 30) -> dict:
        bars = self.broker.get_bars(symbol, timeframe, limit)
        return {
            "symbol": symbol,
            "bars": [
                {
                    "timestamp": b.timestamp.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in bars
            ],
        }

    def _tool_get_quote(self, symbol: str) -> dict:
        return {"symbol": symbol, "price": self.broker.get_quote(symbol)}

    def _tool_place_order(self, symbol: str, qty: float, side: str, reason: str) -> dict:
        account = self.broker.get_account()
        positions = self.broker.get_positions()
        price = self.broker.get_quote(symbol)

        self.risk_manager.validate_order(symbol, qty, side, price, account, positions)

        order = self.broker.place_order(symbol, qty, side)
        self.logger.log_event(
            "order_placed",
            {"symbol": symbol, "qty": qty, "side": side, "reason": reason, "order_id": order.id, "status": order.status},
        )
        return {"id": order.id, "symbol": order.symbol, "qty": order.qty, "side": order.side, "status": order.status}
