from pathlib import Path
from unittest.mock import patch

import pytest

from ratpass import storage
from ratpass.providers import CodexProvider
from ratpass.session import Session
from ratpass.types import Credential


@pytest.fixture
def creds() -> Credential:
    return Credential("oauth", "codex", "old-refresh", "old-access", 0, {})


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


def test_load_missing_credentials() -> None:
    assert Session.load("codex") is None


def test_load_selects_provider_from_credentials(creds: Credential) -> None:
    storage.save(creds)
    with patch(
        "ratpass.session.Providers.create_provider",
        return_value=CodexProvider("app_test"),
    ) as factory:
        session = Session.load("codex")
    factory.assert_called_once_with("codex")
    assert session is not None
    assert session.credentials == creds


def test_login_saves_credentials(creds: Credential) -> None:
    provider = CodexProvider("app_test")
    with patch.object(provider, "auth", return_value=creds) as auth:
        session = Session.login("codex", provider=provider, headless=True)
    auth.assert_called_once_with(headless=True)
    assert session.credentials == storage.load("codex") == creds


def test_refresh_rotates_and_saves_credentials(creds: Credential) -> None:
    session = Session(CodexProvider("app_test"), creds)
    options = session.openai_options()
    assert options == {
        "api_key": "old-access",
        "base_url": "https://chatgpt.com/backend-api/codex",
    }
    with patch(
        "ratpass.providers.codex._request",
        return_value={
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 60,
        },
    ):
        refreshed = session.refresh()
    assert refreshed == session.credentials == storage.load("codex")
    assert refreshed.refresh == "new-refresh"
    assert refreshed.access == "new-access"
    assert session.openai_options()["api_key"] == "new-access"
    assert options["api_key"] == "old-access"


def test_refresh_retains_credentials_when_save_fails(creds: Credential) -> None:
    session = Session(CodexProvider("app_test"), creds)
    with (
        patch(
            "ratpass.providers.codex._request",
            return_value={
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 60,
            },
        ),
        patch("ratpass.storage.save", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        session.refresh()
    assert session.credentials.refresh == "new-refresh"
    session.save()
    assert storage.load("codex") == session.credentials
