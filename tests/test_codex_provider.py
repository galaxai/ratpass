import base64
import json
import urllib.request
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse

import pytest

from ratpass.metadata import PROJECT_NAME, USER_AGENT
from ratpass.providers.base import Pkce
from ratpass.providers.codex import CodexProvider
from ratpass.storage import load


def _jwt(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    return f"header.{encoded.decode()}.signature"


def test_authorize_url_contains_codex_parameters() -> None:
    provider = CodexProvider("app_test")
    url = provider.authorize_url(
        "http://localhost:1455/auth/callback",
        Pkce(verifier="secret", challenge="challenge"),
        "state",
    )

    assert urlparse(url).path == "/oauth/authorize"
    query = parse_qs(urlparse(url).query)
    assert query["client_id"] == ["app_test"]
    assert query["code_challenge"] == ["challenge"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["state"]
    assert query["originator"] == [PROJECT_NAME]


def test_exchange_sends_authorization_code_and_verifier() -> None:
    provider = CodexProvider("app_test")
    tokens = {
        "access_token": "access",
        "refresh_token": "refresh",
    }
    with patch("ratpass.providers.base._request", return_value=tokens) as request:
        result = provider.exchange(
            "authorization-code",
            "http://localhost:1455/auth/callback",
            Pkce(verifier="verifier", challenge="challenge"),
        )

    assert result == tokens
    arguments = request.call_args.kwargs
    body = parse_qs(arguments["body"])
    assert body["code"] == ["authorization-code"]
    assert body["code_verifier"] == ["verifier"]
    assert body["client_id"] == ["app_test"]
    assert arguments["headers"]["User-Agent"] == USER_AGENT


def test_token_response_becomes_credential() -> None:
    provider = CodexProvider("app_test")
    id_token = _jwt({"chatgpt_account_id": "account-123"})

    with patch("ratpass.providers.codex.time.time", return_value=100.0):
        credential = provider.credential_from_tokens(
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "id_token": id_token,
                "expires_in": 60,
            }
        )

    assert credential.type == "oauth"
    assert credential.method_id == "codex"
    assert credential.access == "access"
    assert credential.refresh == "refresh"
    assert credential.expires == 160_000
    assert credential.metadata == {"id_token": id_token}


def test_browser_flow_receives_callback_and_returns_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    provider = CodexProvider("app_test", callback_port=0, timeout=2)
    tokens = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 60,
    }

    def complete_login(authorization_url: str) -> None:
        query = parse_qs(urlparse(authorization_url).query)
        callback = query["redirect_uri"][0]
        separator = "&" if "?" in callback else "?"
        callback += separator + urlencode({"code": "code", "state": query["state"][0]})
        with urllib.request.urlopen(callback, timeout=2) as response:
            assert response.status == 200

    with patch.object(provider, "exchange", return_value=tokens) as exchange:
        credential = provider.browser_authorize(opener=complete_login)

    exchange.assert_called_once()
    assert credential.access == "access"
    assert load("codex") == credential


def test_headless_flow_is_not_implemented_yet() -> None:
    # TODO: the device-code flow lands in the next PR; until then the provider
    # must fail loudly instead of silently returning a bad credential.
    provider = CodexProvider("app_test")

    with pytest.raises(NotImplementedError):
        provider.headless_authorize()


def test_refresh_keeps_refresh_token_when_server_does_not_rotate_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    provider = CodexProvider("app_test")
    with patch(
        "ratpass.providers.codex._request",
        return_value={"access_token": "new-access", "expires_in": 60},
    ) as request:
        credential = provider.refresh("existing-refresh")

    body = parse_qs(request.call_args.kwargs["body"])
    assert body["grant_type"] == ["refresh_token"]
    assert body["refresh_token"] == ["existing-refresh"]
    assert credential.refresh == "existing-refresh"
    assert credential.access == "new-access"
    assert load("codex") == credential
