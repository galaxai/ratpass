"""Runtime configuration for RatPass."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CLIENT_ID_ENV = "CLIENT_ID"


class ConfigError(ValueError):
    """Raised when RatPass configuration is invalid."""


def _read_dotenv_value(name: str, path: Path) -> str | None:
    """Read one simple KEY=VALUE entry without adding a dotenv dependency."""

    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        key, separator, value = stripped.partition("=")
        if separator and key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value

    return None


@dataclass(frozen=True, slots=True)
class Config:
    """RatPass values loaded from the project-root ``.env`` file."""

    client_id: str | None = None

    @classmethod
    def from_dotenv(cls) -> Config:
        client_id = _read_dotenv_value(CLIENT_ID_ENV, Path.cwd() / ".env")
        return cls(client_id=client_id)
