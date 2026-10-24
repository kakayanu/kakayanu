"""A name-keyed registry of tools the agent may call.

Tools are plain functions wrapped by the Anthropic SDK's ``beta_tool`` decorator,
which derives the JSON schema from the signature and docstring. Keeping the
registry separate from the agent means a tool can be added, swapped, or left out
of a run without touching the agent loop.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from anthropic import beta_tool


class DuplicateToolError(ValueError):
    """Raised when two tools claim the same name."""


class ToolRegistry:
    """Holds the tools available to an agent run."""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, fn: Callable[..., str]) -> Callable[..., str]:
        """Decorator: add ``fn`` to the registry and return it unchanged.

        The function is returned as-is so it stays directly callable (and
        testable); the SDK-wrapped copy is what the registry hands the agent.
        """
        name = fn.__name__
        if name in self._tools:
            raise DuplicateToolError(f"a tool named {name!r} is already registered")
        if not (fn.__doc__ or "").strip():
            raise ValueError(
                f"tool {name!r} needs a docstring -- Claude reads it as the description"
            )
        self._tools[name] = beta_tool(fn)
        return fn

    def names(self) -> list[str]:
        return sorted(self._tools)

    def tools(self, *, only: list[str] | None = None) -> list[Any]:
        """The SDK tool objects to pass to ``tool_runner(tools=...)``.

        ``only`` restricts the run to the named subset; an unknown name is an error
        rather than a silent omission.
        """
        if only is None:
            return [self._tools[name] for name in self.names()]
        missing = [name for name in only if name not in self._tools]
        if missing:
            raise KeyError(f"unknown tool(s): {', '.join(missing)}")
        return [self._tools[name] for name in only]

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())
