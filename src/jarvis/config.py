"""Runtime configuration, resolved from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 16000

VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")

SYSTEM_PROMPT = """You are Jarvis, a command-line assistant.

Use the tools you are given rather than guessing at facts you can look up. When a
tool call fails, say what failed instead of inventing a result. Keep answers short
unless the user asks for detail.
"""


class ConfigError(ValueError):
    """Raised when the environment holds a value Jarvis cannot use."""


@dataclass(frozen=True)
class Settings:
    """Everything the agent needs to know before its first request."""

    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    max_tokens: int = DEFAULT_MAX_TOKENS
    workspace: Path = Path()
    system_prompt: str = SYSTEM_PROMPT

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env

        effort = source.get("JARVIS_EFFORT", DEFAULT_EFFORT).strip().lower()
        if effort not in VALID_EFFORTS:
            raise ConfigError(
                f"JARVIS_EFFORT must be one of {', '.join(VALID_EFFORTS)}, got {effort!r}"
            )

        raw_max_tokens = source.get("JARVIS_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)).strip()
        try:
            max_tokens = int(raw_max_tokens)
        except ValueError as exc:
            raise ConfigError(
                f"JARVIS_MAX_TOKENS must be an integer, got {raw_max_tokens!r}"
            ) from exc
        if max_tokens < 1:
            raise ConfigError(f"JARVIS_MAX_TOKENS must be positive, got {max_tokens}")

        return cls(
            model=source.get("JARVIS_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            effort=effort,
            max_tokens=max_tokens,
            workspace=Path(source.get("JARVIS_WORKSPACE", ".")).expanduser().resolve(),
        )
