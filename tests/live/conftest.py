"""Shared credentials for opt-in live SDK tests."""

import os
import struct
import time
import zlib

import pytest

from ratpass.providers import CodexProvider
from ratpass.storage import load


@pytest.fixture(scope="module")
def model():
    return os.environ.get("OPENAI_TEST_MODEL", "gpt-5.6-luna")


@pytest.fixture(scope="module")
def client_options():
    credential = load("codex")
    if credential is None:
        pytest.fail("No saved Codex credentials. Run CodexProvider().auth() first.")
    if credential.expires <= (time.time() + 60) * 1000:
        credential = CodexProvider().refresh(credential.refresh)
    return {
        "api_key": credential.access,
        "base_url": "https://chatgpt.com/backend-api/codex",
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
