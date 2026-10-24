# Jarvis

A Claude-powered command-line assistant: an agent loop over the Anthropic API with
a pluggable tool registry.

## Status

Scaffold. The agent loop, tool registry, config handling, CLI, and tests are in
place and exercised; the tool set is three read-only examples meant to be replaced.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env    # then fill in ANTHROPIC_API_KEY
```

Credentials: the SDK resolves `ANTHROPIC_API_KEY`, then `ANTHROPIC_AUTH_TOKEN`, then a
profile stored by `ant auth login` — so if you've logged in with the CLI, you can skip
the key entirely.

## Use

```bash
jarvis                      # interactive REPL
jarvis -p "what time is it" # one-shot
python -m jarvis            # same, without installing the script
```

In the REPL: `/reset` clears the conversation, `/exit` (or Ctrl-D) quits.

## Configuration

All optional — see `.env.example`.

| Variable | Default | Meaning |
|---|---|---|
| `JARVIS_MODEL` | `claude-opus-5-5` | Model ID |
| `JARVIS_EFFORT` | `medium` | `low`, `medium`, `high`, `xhigh`, or `max` |
| `JARVIS_MAX_TOKENS` | `16000` | Per-response output cap |
| `JARVIS_WORKSPACE` | `.` | Directory the filesystem tools may read |

Bad values fail at startup with a message, not mid-conversation.

## Layout

```
src/jarvis/
  config.py          Settings.from_env() — validated, frozen
  agent.py           the turn loop: history mirroring, pause-turn resume, refusals
  cli.py             argparse + REPL
  tools/
    registry.py      ToolRegistry: name-keyed, schema from signature + docstring
    builtin.py       the shipped tools, built over a Settings via build_registry()
tests/               26 tests, no network and no API key required
```

## Adding a tool

Write a function with type hints and a docstring, and register it. The Anthropic SDK
derives the JSON schema from the signature; the docstring is what Claude reads to
decide when to call it, so write it for that audience.

```python
@registry.register
def search_notes(query: str, limit: int = 5) -> str:
    """Search the user's notes.

    Args:
        query: What to search for.
        limit: Maximum number of results.
    """
    return "\n".join(find(query)[:limit])
```

Two conventions worth keeping: return a string (Claude reads it as text), and catch
expected failures to return `f"error: {exc}"` rather than raising — the model can
recover from a reported error, but an exception ends the turn.

## Design notes

- **Effort is set explicitly.** `claude-opus-5-5` defaults to `medium`; pinning it
  means a future change to that default won't silently alter behaviour or cost.
- **Refusal fallbacks are on.** Requests go out with `fallbacks="default"`, so a
  safety decline is re-run on a fallback model inside the same call instead of just
  stopping. Remove `fallbacks`/`betas` in `agent.py` if you'd rather see the refusal.
- **Paused turns are resumed.** The SDK's tool runner exits silently on
  `stop_reason: "pause_turn"`, which would look like a short answer rather than a
  bug. `Agent._run_turn` mirrors history and restarts, capped at 5 resumes.
- **No shell tool.** Giving the model arbitrary host execution is a decision to make
  deliberately, not to inherit from a scaffold. Filesystem reads are confined to
  `JARVIS_WORKSPACE`, with symlinks resolved before the boundary check.
- **No prompt caching yet.** The system prompt is far below the minimum cacheable
  prefix (512–4096 tokens, model-dependent), so a `cache_control` breakpoint would
  silently do nothing. Add one once the prompt grows.

## Not built yet

Streaming output (the REPL blocks until a turn completes), conversation persistence,
token/cost accounting, and context management for conversations that outgrow the
window.

## Development

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```
