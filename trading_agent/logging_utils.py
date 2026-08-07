import json
from datetime import datetime, timezone
from pathlib import Path


class TradeLogger:
    """Append-only JSONL audit trail of every tool call, order, and rejection."""

    def __init__(self, path: str = "logs/trading_agent.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event_type: str, data: dict) -> None:
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event_type, **data}
        with self.path.open("a") as f:
            f.write(json.dumps(record) + "\n")
