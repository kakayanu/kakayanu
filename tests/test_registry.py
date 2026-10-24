import pytest

from jarvis.config import Settings
from jarvis.tools.builtin import build_registry
from jarvis.tools.registry import DuplicateToolError, ToolRegistry


def test_register_returns_the_plain_function():
    registry = ToolRegistry()

    @registry.register
    def echo(text: str) -> str:
        """Echo the given text.

        Args:
            text: What to echo back.
        """
        return text

    assert echo("hi") == "hi"
    assert registry.names() == ["echo"]
    assert len(registry.tools()) == 1


def test_duplicate_names_are_rejected():
    registry = ToolRegistry()

    @registry.register
    def tick() -> str:
        """Tick once."""
        return "tick"

    with pytest.raises(DuplicateToolError):
        registry.register(tick)


def test_a_tool_without_a_docstring_is_rejected():
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="docstring"):

        @registry.register
        def undocumented() -> str:
            return ""


def test_tools_subset_rejects_unknown_names():
    registry = build_registry(Settings.from_env({}))
    assert "current_time" in registry.names()

    with pytest.raises(KeyError):
        registry.tools(only=["not_a_tool"])

    assert len(registry.tools(only=["current_time"])) == 1
