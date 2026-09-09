"""Sessions that coordinate provider authentication and credential persistence."""

from typing import Self

from ratpass import storage
from ratpass.providers import BaseProvider, Credential, Providers
from ratpass.types import OpenAIOptions


class Session:
    """Hold current credentials and save them after login or explicit refresh."""

    def __init__(self, provider: BaseProvider, creds: Credential) -> None:
        """Bind credentials to a provider without performing I/O.

        Raises:
            ValueError: If the credentials belong to another provider.
        """
        if creds.method_id != provider.method_id:
            raise ValueError("Credential does not belong to this provider")

        self._provider = provider
        self._creds = creds

    @property
    def credentials(self) -> Credential:
        """Return the current credentials without refreshing."""
        return self._creds

    @classmethod
    def load(cls, method_id: str) -> Self | None:
        """Load saved credentials and construct their configured provider.

        Return None if no credentials exist. Storage and provider configuration
        errors propagate; this method does not log in or refresh tokens.
        """
        creds = storage.load(method_id)
        if creds is None:
            return None
        return cls.from_credentials(creds)

    @classmethod
    def from_credentials(cls, creds: Credential) -> Self:
        """Create the configured provider identified by creds.method_id.

        Provider lookup and configuration errors propagate. Credentials are
        neither refreshed nor saved.
        """
        provider = Providers.create_provider(creds.method_id)
        return cls(provider, creds)

    @classmethod
    def login(
        cls,
        method_id: str,
        *,
        provider: BaseProvider | None = None,
        headless: bool = False,
    ) -> Self:
        """Authorize through the supplied or configured provider and save credentials.

        Use browser login unless headless is True. Raise ValueError if the
        provider does not match method_id; authorization and save errors propagate.
        """
        if provider is None:
            provider = Providers.create_provider(method_id)
        if provider.method_id != method_id:
            raise ValueError("Provider does not match requested method")

        creds = provider.auth(headless=headless)
        session = cls(provider, creds)
        session.save()
        return session

    def refresh(self) -> Credential:
        """Refresh unconditionally, save, and return the new credentials.

        Refresh errors leave current credentials unchanged. Save errors propagate
        after updating the credentials in memory, allowing save() to be retried.
        """
        creds = self._provider.refresh(self._creds.refresh)

        # Retain the new token in memory even if saving fails.
        self._creds = creds
        self.save()
        return creds

    def openai_options(self) -> OpenAIOptions:
        """Return client options using current credentials without refreshing.

        Options are a snapshot; refreshing this session does not update options
        or clients previously created from them.
        """
        return self._provider.openai_options(self._creds)

    def save(self) -> None:
        """Save current credentials to default storage; propagate write failures."""
        storage.save(self._creds)
