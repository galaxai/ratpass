from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pkce:
    verifier: str  # the secret we keep
    challenge: str  # SHA-256(verifier)


@dataclass(frozen=True, slots=True)
class Credential:
    type: str
    method_id: str
    refresh: str
    access: str
    expires: float
    metadata: dict
