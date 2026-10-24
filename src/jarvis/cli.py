"""Command-line entry point: one-shot with ``-p``, otherwise an interactive REPL."""

from __future__ import annotations

import argparse
import sys

import anthropic

from jarvis import __version__
from jarvis.agent import Agent, AgentError
from jarvis.config import ConfigError, Settings
from jarvis.tools.builtin import build_registry

PROMPT = "you> "
BANNER = (
    "jarvis {version} -- model {model}, effort {effort}, tools: {tools}\n"
    "Ctrl-D or /exit to quit, /reset to clear history."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="A Claude-powered assistant.")
    parser.add_argument("-p", "--prompt", help="run a single prompt and exit")
    parser.add_argument("--version", action="version", version=f"jarvis {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    registry = build_registry(settings)

    try:
        agent = Agent(settings, registry)
    except anthropic.AnthropicError as exc:
        # Most often a missing credential: no ANTHROPIC_API_KEY and no stored profile.
        print(f"could not start: {exc}", file=sys.stderr)
        return 2

    if args.prompt:
        return _run_once(agent, args.prompt)
    return _run_repl(agent, settings, registry)


def _run_once(agent: Agent, prompt: str) -> int:
    try:
        print(agent.send(prompt))
    except (AgentError, anthropic.APIError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_repl(agent: Agent, settings: Settings, registry) -> int:
    print(
        BANNER.format(
            version=__version__,
            model=settings.model,
            effort=settings.effort,
            tools=", ".join(registry.names()),
        )
    )
    while True:
        try:
            line = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue
        if line in ("/exit", "/quit"):
            return 0
        if line == "/reset":
            agent.reset()
            print("history cleared.")
            continue

        try:
            print(agent.send(line))
        except (AgentError, anthropic.APIError) as exc:
            # Keep the session alive -- one failed turn shouldn't end the REPL.
            print(f"error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
