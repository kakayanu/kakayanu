# trading_agent

An agentic trading system: Claude decides *what* to do by calling tools, a
deterministic risk manager decides *what's allowed*, and a broker-agnostic
interface executes it. Paper/sandbox trading by default.

## Architecture

```
trading_agent/
  brokers/        broker-agnostic interface + Alpaca (stocks) and ccxt (crypto) adapters
  risk/           hard-coded guardrails (position size, order size, daily loss halt) —
                   these are plain Python, not prompted, so the LLM cannot reason past them
  agent/          Claude tool-use loop: get_account_state, get_positions, get_market_data,
                   get_quote, place_order (place_order is validated by the risk manager)
  backtest/       deterministic strategy backtester, for validating rule-based strategies
                   before wiring them into (or comparing them against) the live agent
  logging_utils.py  append-only JSONL audit trail of every tool call, order, and rejection
  main.py         CLI entrypoint: runs one decision cycle
```

Everything the agent does goes through `TradingToolkit`, and every order goes
through `RiskManager.validate_order` before it reaches the broker. The risk
limits are not suggestions in a prompt — they're enforced in code the model
has no path around.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY and broker keys
```

- Alpaca: sign up for paper trading keys at https://app.alpaca.markets/paper/dashboard/overview
  (no real money involved).
- ccxt/Binance: use testnet keys, e.g. https://testnet.binance.vision/.

## Run a decision cycle

```bash
python -m trading_agent.main --broker alpaca --symbols AAPL,MSFT
python -m trading_agent.main --broker ccxt --exchange binance --symbols BTC/USDT,ETH/USDT
```

Each run: the agent inspects account state, positions, and market data for the
given symbols, optionally places orders (rejected automatically if they'd
violate the configured risk limits), and prints a summary. Every event is also
appended to `logs/trading_agent.jsonl`.

## Backtest a rule-based strategy

```python
from trading_agent.backtest.engine import moving_average_crossover, run_backtest
from trading_agent.brokers.alpaca_broker import AlpacaBroker

broker = AlpacaBroker(paper=True)
bars = broker.get_bars("AAPL", "1Day", limit=200)
result = run_backtest("AAPL", bars, moving_average_crossover(fast=5, slow=20))
print(result.return_pct, len(result.trades))
```

## Tests

```bash
pytest
```

Tests cover the risk manager and backtester with no network calls; broker
adapters aren't unit tested here since they're thin wrappers over
Alpaca/ccxt — exercise them against paper/testnet accounts directly.

## Safety notes

- Defaults are paper/sandbox everywhere (`paper=True`, `sandbox=True`). Going
  live means explicitly passing `paper=False` / `sandbox=False` and supplying
  real credentials — treat that as a deliberate, reviewed decision, not a flag
  flip.
- Risk limits (`MAX_POSITION_PCT`, `MAX_ORDER_NOTIONAL`, `MAX_DAILY_LOSS_PCT`,
  `MAX_OPEN_POSITIONS`, `ALLOWED_SYMBOLS`) live in `.env` and are enforced in
  `RiskManager`, independent of the LLM. Tighten them before pointing this at
  anything resembling real capital.
- The LLM is used for interpretation and strategy selection, not as the
  source of truth for arithmetic — position sizing and PnL are computed in
  plain Python, not trusted from model output.
- This is a scaffold, not investment advice or a production trading system.

## Requires

Python 3.10+ (uses `X | None` union syntax and builtin generic types).
