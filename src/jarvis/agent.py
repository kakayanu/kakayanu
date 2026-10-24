"""The agent loop.

The SDK's beta tool runner drives request -> tool execution -> request for us, so
this module owns only the parts the runner leaves to the caller: mirroring the
conversation history across turns, restarting a turn the server paused, and
turning the final message into text.
"""

from __future__ import annotations

from typing import Any

import anthropic

from jarvis.config import Settings
from jarvis.tools.registry import ToolRegistry

# A paused turn ends the runner's loop silently, so cap how many times we resume
# one before giving up rather than looping forever.
MAX_PAUSE_RESTARTS = 5

# Server-side refusal fallback: if a safety classifier declines the request, the
# API re-runs it on a fallback model inside the same call instead of just stopping.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AgentError(RuntimeError):
    """Raised when a turn cannot be completed."""


class Agent:
    """A stateful conversation with Claude over a fixed set of tools."""

    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry
        # A bare constructor resolves ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or a
        # stored `ant auth login` profile -- in that order. Don't pass a key here.
        self.client = client or anthropic.Anthropic()
        self.messages: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Drop the conversation history, keeping settings and tools."""
        self.messages = []

    def send(self, user_message: str) -> str:
        """Run one turn to completion and return Claude's final text."""
        self.messages.append({"role": "user", "content": user_message})
        final = self._run_turn()

        if final is None:
            raise AgentError("the model returned no message")
        if final.stop_reason == "refusal":
            detail = getattr(final.stop_details, "explanation", None) or "no explanation given"
            raise AgentError(f"the request was declined ({detail})")

        return _text_of(final)

    def _run_turn(self) -> Any:
        """Drive the tool runner, resuming across paused turns."""
        restarts = 0
        while True:
            runner = self.client.beta.messages.tool_runner(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=self.settings.system_prompt,
                thinking={"type": "adaptive"},
                output_config={"effort": self.settings.effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
                tools=self.registry.tools(),
                messages=self.messages,
            )

            final = None
            for message in runner:
                final = message
                # The runner keeps its own history and does not expose it, so mirror
                # every turn here -- otherwise a restart loses the conversation.
                self.messages.append({"role": "assistant", "content": message.content})
                tool_response = runner.generate_tool_call_response()
                if tool_response is not None:
                    self.messages.append(tool_response)

            if final is None or final.stop_reason != "pause_turn":
                return final

            restarts += 1
            if restarts > MAX_PAUSE_RESTARTS:
                raise AgentError(f"turn still paused after {MAX_PAUSE_RESTARTS} restarts")
            # `self.messages` already ends with the paused assistant turn, so the
            # next runner picks up where this one stopped.


def _text_of(message: Any) -> str:
    """Join the text blocks of a message, ignoring thinking and tool blocks."""
    parts = [block.text for block in message.content if block.type == "text"]
    return "\n".join(part for part in parts if part).strip()
