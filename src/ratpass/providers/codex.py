"""Codex-specific OAuth provider."""

from __future__ import annotations

import time
import urllib.parse
from collections.abc import Mapping
from typing import Any

from ratpass.config import CLIENT_ID_ENV, Config, ConfigError
from ratpass.metadata import PROJECT_NAME
from ratpass.providers.base import (
    CALLBACK_PORT,
    AuthorizationError,
    BaseProvider,
    _request,
)
from ratpass.providers.types import Credential, Pkce

ISSUER = "https://auth.openai.com"
# POLLING_SAFETY_MARGIN = 3.0


class CodexProvider(BaseProvider):
    """Authenticate through the Codex OAuth application."""

    method_id = "codex"

    def __init__(
        self,
        client_id: str | None = None,
        *,
        issuer: str = ISSUER,
        callback_port: int = CALLBACK_PORT,
        timeout: float = 600.0,
    ) -> None:
        configured_client_id = client_id or Config.from_dotenv().client_id
        if not configured_client_id:
            raise ConfigError(f"{CLIENT_ID_ENV} must be set in .env")
        super().__init__(
            client_id=configured_client_id,
            issuer=issuer,
            callback_port=callback_port,
            timeout=timeout,
        )

    def authorize_url(self, redirect: str, pkce: Pkce, state: str) -> str:
        """Retruns authorize url for codex provider"""
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": redirect,
                "scope": (
                    "openid profile email offline_access "
                    "api.connectors.read api.connectors.invoke"
                ),
                "code_challenge": pkce.challenge,
                "code_challenge_method": "S256",
                "id_token_add_organizations": "true",
                "codex_cli_simplified_flow": "true",
                "state": state,
                "originator": PROJECT_NAME,
            }
        )
        return f"{self.issuer}/oauth/authorize?{query}"

    def credential_from_tokens(self, tokens: Mapping[str, Any]) -> Credential:
        """Extracts and validated credential from tokens"""
        refresh = tokens.get("refresh_token")
        access = tokens.get("access_token")
        expires_in = tokens.get("expires_in")
        # Validate
        if not isinstance(expires_in, (int, float)) or expires_in < 0:
            raise AuthorizationError("Token response contains an invalid expires_in")
        if not isinstance(access, str) or not access:
            raise AuthorizationError("Token response contains invalid access_token")
        if not isinstance(refresh, str) or not refresh:
            raise AuthorizationError("Token response contains invalid refresh_token")
        metadata: dict[str, Any] = {}
        id_token = tokens.get("id_token")
        if isinstance(id_token, str) and id_token:
            metadata["id_token"] = id_token

        return Credential(
            type="oauth",
            method_id=self.method_id,
            refresh=refresh,
            access=access,
            expires=time.time() * 1000 + float(expires_in) * 1000,
            metadata=metadata,
        )

    def refresh(self, refresh_token: str) -> Credential:
        """Use a Codex refresh token to obtain a fresh credential."""

        if not refresh_token:
            raise ValueError("refresh_token must not be empty")
        tokens = _request(
            f"{self.issuer}/oauth/token",
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
            body=urllib.parse.urlencode(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                }
            ),
        )
        tokens.setdefault("refresh_token", refresh_token)
        return self.credential_from_tokens(tokens)

    def headless_authorize(self) -> Credential:
        raise NotImplementedError
