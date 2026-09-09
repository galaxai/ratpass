"""Shared credential model."""

from dataclasses import dataclass
from enum import StrEnum


class ProviderId(StrEnum):
    """Stable identifiers used to save and load provider credentials."""

    CODEX = "codex"


@dataclass(frozen=True, slots=True)
class Credential:
    type: str
    method_id: str
    refresh: str
    access: str
    expires: float
    metadata: dict
