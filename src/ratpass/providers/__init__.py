"""Authentication providers shipped with RatPass."""

from enum import Enum

from ratpass.providers.base import AuthorizationError, BaseProvider, Pkce
from ratpass.providers.codex import CodexProvider
from ratpass.types import Credential, ProviderId


class Providers(Enum):
    """Provider implementations keyed by their ProviderId member names."""

    CODEX = CodexProvider

    @classmethod
    def create_provider(cls, method_id: str) -> BaseProvider:
        """Return a new provider for a stored method identifier.

        Raises:
            ValueError: If the identifier is unknown or has no registered provider.
            ratpass.config.ConfigError: If required provider configuration is missing.

        Other exceptions from provider initialization propagate to the caller.
        """
        try:
            provider_id = ProviderId(method_id)
            member = cls[provider_id.name]
        except (ValueError, KeyError):  # fmt: skip
            raise ValueError(f"Unknown provider: {method_id}") from None

        return member.value()


__all__ = [
    "AuthorizationError",
    "BaseProvider",
    "CodexProvider",
    "Credential",
    "Pkce",
    "ProviderId",
    "Providers",
]
