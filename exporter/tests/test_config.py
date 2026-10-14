import pytest

from gcups_exporter.config import Config, ConfigError


def test_defaults():
    config = Config.from_env({"GCUPS_PASSWORD": "secret"})

    assert config == Config(
        gcups_url="http://gcups:8080", gcups_password="secret", timeout_seconds=5.0, port=9199,
    )


def test_trailing_slash_is_removed_from_url():
    config = Config.from_env({"GCUPS_PASSWORD": "x", "GCUPS_URL": "http://ups:8080/"})

    assert config.gcups_url == "http://ups:8080"


@pytest.mark.parametrize("env, message", [
    ({}, "GCUPS_PASSWORD is required"),
    ({"GCUPS_PASSWORD": "x", "EXPORTER_PORT": "abc"}, "EXPORTER_PORT must be a number"),
    ({"GCUPS_PASSWORD": "x", "GCUPS_TIMEOUT": "0"}, "GCUPS_TIMEOUT must be positive"),
])
def test_invalid_env_is_rejected(env, message):
    with pytest.raises(ConfigError, match=message):
        Config.from_env(env)
