from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from ratpass.providers.base import Pkce
from ratpass.providers.codex import CodexProvider


def test_uses_configured_client_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("CLIENT_ID=app_test\n")
    monkeypatch.chdir(tmp_path)

    url = CodexProvider().authorize_url(
        "http://localhost:1455/auth/callback",
        Pkce(verifier="verifier", challenge="challenge"),
        "state",
    )

    query = parse_qs(urlparse(url).query)
    assert query["client_id"] == ["app_test"]
