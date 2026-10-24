import pytest

from jarvis.config import DEFAULT_EFFORT, DEFAULT_MODEL, ConfigError, Settings


def test_defaults_when_env_is_empty():
    settings = Settings.from_env({})
    assert settings.model == DEFAULT_MODEL
    assert settings.effort == DEFAULT_EFFORT
    assert settings.max_tokens == 16000
    assert settings.workspace.is_absolute()


def test_env_overrides_are_applied():
    settings = Settings.from_env(
        {"JARVIS_MODEL": "claude-sonnet-5-5", "JARVIS_EFFORT": "HIGH", "JARVIS_MAX_TOKENS": "2048"}
    )
    assert settings.model == "claude-sonnet-5-5"
    assert settings.effort == "high"
    assert settings.max_tokens == 2048


@pytest.mark.parametrize(
    "env",
    [
        {"JARVIS_EFFORT": "turbo"},
        {"JARVIS_MAX_TOKENS": "lots"},
        {"JARVIS_MAX_TOKENS": "0"},
    ],
)
def test_bad_values_are_rejected(env):
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_workspace_is_resolved_to_an_absolute_path(tmp_path):
    settings = Settings.from_env({"JARVIS_WORKSPACE": str(tmp_path)})
    assert settings.workspace == tmp_path.resolve()
