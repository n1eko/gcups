"""Exporter configuration, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class ConfigError(ValueError):
    """Raised when an environment variable is missing or invalid."""


@dataclass(frozen=True)
class Config:
    gcups_url: str
    gcups_password: str
    timeout_seconds: float
    port: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> Config:
        password = env.get("GCUPS_PASSWORD", "")
        if not password:
            raise ConfigError("GCUPS_PASSWORD is required")

        return cls(
            gcups_url=env.get("GCUPS_URL", "http://gcups:8080").rstrip("/"),
            gcups_password=password,
            timeout_seconds=_parse_number(env, "GCUPS_TIMEOUT", "5", float),
            port=_parse_number(env, "EXPORTER_PORT", "9199", int),
        )


def _parse_number(env: Mapping[str, str], name: str, default: str, kind: type):
    raw = env.get(name, default)
    try:
        value = kind(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from None
    if value <= 0:
        raise ConfigError(f"{name} must be positive, got {raw!r}")
    return value
