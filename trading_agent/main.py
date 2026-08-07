import argparse

from .agent.claude_agent import ClaudeTradingAgent
from .agent.tools import TradingToolkit
from .brokers.alpaca_broker import AlpacaBroker
from .brokers.base import Broker
from .brokers.ccxt_broker import CCXTBroker
from .config import load_risk_limits
from .logging_utils import TradeLogger
from .risk.manager import RiskManager


def build_broker(args: argparse.Namespace) -> Broker:
    if args.broker == "alpaca":
        return AlpacaBroker(paper=True)
    if args.broker == "ccxt":
        return CCXTBroker(exchange_id=args.exchange, sandbox=True)
    raise ValueError(f"Unknown broker {args.broker}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one decision cycle of the agentic trading system.")
    parser.add_argument("--broker", choices=["alpaca", "ccxt"], default="alpaca")
    parser.add_argument("--exchange", default="binance", help="ccxt exchange id, used when --broker ccxt")
    parser.add_argument("--symbols", default="AAPL,MSFT", help="Comma-separated symbols to consider")
    args = parser.parse_args()

    broker = build_broker(args)
    risk_manager = RiskManager(load_risk_limits())
    logger = TradeLogger()
    toolkit = TradingToolkit(broker, risk_manager, logger)
    agent = ClaudeTradingAgent(toolkit)

    risk_manager.start_of_day(broker.get_account())

    instruction = (
        f"Review the current account state and the following symbols: {args.symbols}. "
        "Decide whether to open, close, or hold any positions this cycle, and act via your tools."
    )
    summary = agent.run_cycle(instruction)
    logger.log_event("cycle_summary", {"summary": summary})
    print(summary)


if __name__ == "__main__":
    main()
