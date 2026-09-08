from pathlib import Path

import pytest

from ratpass.config import Config


def test_client_id_is_loaded_from_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("CLIENT_ID=app_from_dotenv\n")
    monkeypatch.chdir(tmp_path)

    assert Config.from_dotenv().client_id == "app_from_dotenv"
