"""Local credential persistence with atomic, owner-only files."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from ratpass.types import Credential


def _resolve_directory(directory: str | Path | None) -> Path:
    if directory is not None:
        return Path(directory)
    return Path.home() / ".ratpass" / "credentials"


def save(credential: Credential, *, directory: str | Path | None = None) -> None:
    """Atomically replace the saved credential; propagate any write failure."""
    directory = _resolve_directory(directory)
    path = directory / f"{credential.method_id}.json"
    payload = json.dumps(asdict(credential), allow_nan=False) + "\n"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load(method_id: str, *, directory: str | Path | None = None) -> Credential | None:
    """Return the saved credential, or None when no credential exists."""
    directory = _resolve_directory(directory)
    path = directory / f"{method_id}.json"
    try:
        payload = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        credential = Credential(**json.loads(payload))
        if credential.method_id != method_id:
            raise ValueError
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid credential file: {path}") from error
    return credential
