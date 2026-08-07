import json
import os

import anthropic

from .tools import TOOL_SCHEMAS, TradingToolkit

SYSTEM_PROMPT = """You are a disciplined trading agent operating on a paper/sandbox brokerage account.

Rules:
- You may only act through the provided tools. You cannot bypass risk checks: place_order is rejected
  automatically if it violates hard-coded risk limits (position size, order notional, daily loss halt).
- Always check account state and positions before proposing new trades.
- Prefer no action over a low-conviction trade. State your reasoning briefly before each trade.
- After analyzing and (optionally) placing orders, give a short summary of what you did and why.
"""


class ClaudeTradingAgent:
    def __init__(self, toolkit: TradingToolkit, model: str = "claude-sonnet-5", api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model
        self.toolkit = toolkit

    def run_cycle(self, instruction: str, max_turns: int = 8) -> str:
        messages = [{"role": "user", "content": instruction}]

        for _ in range(max_turns):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return "".join(block.text for block in response.content if block.type == "text")

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self.toolkit.dispatch(block.name, block.input)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                    )
            messages.append({"role": "user", "content": tool_results})

        return "Reached max turns without a final answer."
