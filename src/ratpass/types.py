"""Shared credential model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Credential:
    type: str
    method_id: str
    refresh: str
    access: str
    expires: float
    metadata: dict
