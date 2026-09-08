import ntpath
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from ratpass import providers
from ratpass.providers import BaseProvider
from ratpass.storage import load, save
from ratpass.types import Credential


def credential(access: str = "access", method_id: str = "codex") -> Credential:
    return Credential(
        "oauth", method_id, "refresh", access, 123_000, {"id_token": "id"}
    )


def test_round_trip_and_replace(tmp_path: Path) -> None:
    directory = tmp_path / "credentials"
    assert load("codex", directory=directory) is None
    save(credential(), directory=directory)
    assert load("codex", directory=directory) == credential()
    save(credential(method_id="other"), directory=directory)
    save(credential("new-access"), directory=directory)
    assert load("codex", directory=directory) == credential("new-access")
    assert load("other", directory=directory) == credential(method_id="other")
    if os.name == "posix":
        assert (directory.stat().st_mode & 0o777) == 0o700
        assert ((directory / "codex.json").stat().st_mode & 0o777) == 0o600


def test_failed_replace_preserves_previous_credential(tmp_path: Path) -> None:
    directory = tmp_path
    save(credential(), directory=directory)
    with (
        patch("ratpass.storage.os.replace", side_effect=OSError("write failed")),
        pytest.raises(OSError, match="write failed"),
    ):
        save(credential("new-access"), directory=directory)
    assert load("codex", directory=directory) == credential()
    assert list(tmp_path.iterdir()) == [tmp_path / "codex.json"]


@pytest.mark.parametrize(
    "provider",
    [
        value
        for value in vars(providers).values()
        if isinstance(value, type)
        and issubclass(value, BaseProvider)
        and value is not BaseProvider
    ],
    ids=lambda provider: provider.__name__,
)
def test_provider_method_id_is_valid_filename(provider: type[BaseProvider]) -> None:
    method_id = getattr(provider, "method_id", None)
    assert isinstance(method_id, str)
    assert re.fullmatch(r"[A-Za-z0-9_-]+", method_id)
    assert not ntpath.isreserved(method_id)


@pytest.mark.parametrize("payload", ["invalid json", "[]", "{}"])
def test_corrupt_file_is_reported(tmp_path: Path, payload: str) -> None:
    (tmp_path / "codex.json").write_text(payload)
    with pytest.raises(ValueError, match="Invalid credential file"):
        load("codex", directory=tmp_path)
