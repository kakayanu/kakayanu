"""Agent loop tests, driven by a fake tool runner -- no network, no API key."""

from types import SimpleNamespace

import pytest

from jarvis.agent import MAX_PAUSE_RESTARTS, Agent, AgentError
from jarvis.config import Settings
from jarvis.tools.registry import ToolRegistry


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def message(text="", stop_reason="end_turn", stop_details=None):
    return SimpleNamespace(
        content=[text_block(text)] if text else [],
        stop_reason=stop_reason,
        stop_details=stop_details,
    )


class FakeRunner:
    """Yields a canned list of messages, like the SDK runner does."""

    def __init__(self, messages, tool_response=None):
        self._messages = messages
        self._tool_response = tool_response

    def __iter__(self):
        return iter(self._messages)

    def generate_tool_call_response(self):
        return self._tool_response


class FakeClient:
    """Hands out one FakeRunner per turn and records the kwargs it was called with."""

    def __init__(self, runners):
        self._runners = list(runners)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(tool_runner=self._tool_runner))

    def _tool_runner(self, **kwargs):
        self.calls.append(kwargs)
        return self._runners.pop(0)


def make_agent(runners):
    client = FakeClient(runners)
    agent = Agent(Settings.from_env({}), ToolRegistry(), client=client)
    return agent, client


def test_a_simple_turn_returns_the_final_text():
    agent, client = make_agent([FakeRunner([message("hello there")])])

    assert agent.send("hi") == "hello there"
    assert len(client.calls) == 1
    assert agent.messages[0] == {"role": "user", "content": "hi"}


def test_request_carries_the_configured_model_effort_and_fallbacks():
    agent, client = make_agent([FakeRunner([message("ok")])])
    agent.send("hi")

    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"] == {"effort": "medium"}
    assert call["thinking"] == {"type": "adaptive"}
    assert call["fallbacks"] == "default"


def test_tool_results_are_mirrored_into_history():
    tool_response = {"role": "user", "content": [{"type": "tool_result", "content": "42"}]}
    agent, _ = make_agent([FakeRunner([message("done")], tool_response=tool_response)])

    agent.send("compute")

    assert agent.messages[-1] == tool_response


def test_a_paused_turn_is_resumed():
    agent, client = make_agent(
        [
            FakeRunner([message("partial", stop_reason="pause_turn")]),
            FakeRunner([message("complete")]),
        ]
    )

    assert agent.send("search the web") == "complete"
    assert len(client.calls) == 2
    # The second request resumes from the paused assistant turn.
    assert client.calls[1]["messages"] is agent.messages


def test_endless_pausing_gives_up():
    runners = [
        FakeRunner([message("still going", stop_reason="pause_turn")])
        for _ in range(MAX_PAUSE_RESTARTS + 2)
    ]
    agent, _ = make_agent(runners)

    with pytest.raises(AgentError, match="still paused"):
        agent.send("search forever")


def test_a_refusal_is_surfaced_not_returned_as_text():
    refused = message(
        "",
        stop_reason="refusal",
        stop_details=SimpleNamespace(type="refusal", category="cyber", explanation="declined"),
    )
    agent, _ = make_agent([FakeRunner([refused])])

    with pytest.raises(AgentError, match="declined"):
        agent.send("do something disallowed")


def test_an_empty_run_is_an_error():
    agent, _ = make_agent([FakeRunner([])])

    with pytest.raises(AgentError, match="no message"):
        agent.send("hi")


def test_reset_clears_history_but_keeps_tools():
    agent, _ = make_agent([FakeRunner([message("ok")])])
    agent.send("hi")
    assert agent.messages

    agent.reset()
    assert agent.messages == []
    assert agent.registry is not None
