"""Shared credential model."""

from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict


class OpenAIOptions(TypedDict):
    """Provider authentication and endpoint options for an OpenAI client."""

    api_key: str
    base_url: str


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
