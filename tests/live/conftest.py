"""Shared credentials for opt-in live SDK tests."""

import os
import struct
import time
import zlib

import pytest

from ratpass.session import Session


@pytest.fixture(scope="module")
def model():
    return os.environ.get("OPENAI_TEST_MODEL", "gpt-5.6-luna")


@pytest.fixture(scope="module")
def client_options():
    session = Session.load("codex")
    if session is None:
        pytest.fail('No saved Codex credentials. Run Session.login("codex") first.')
    credential = session.credentials
    if credential.expires <= (time.time() + 60) * 1000:
        session.refresh()
    return {
        **session.openai_options(),
        "timeout": 120,
        "max_retries": 0,
    }


@pytest.fixture(scope="module")
def red_png():
    # A 64x64 red PNG fixture, built with stdlib only.
    def chunk(kind, data):
        return (
            struct.pack("!I", len(data))
            + kind
            + data
            + struct.pack("!I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", 64, 64, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\0\0" * 64) * 64))
        + chunk(b"IEND", b"")
    )
