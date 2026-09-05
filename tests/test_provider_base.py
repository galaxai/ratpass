import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from ratpass.providers.codex import CodexProvider
from ratpass.providers.types import Pkce


class AuthorizeUrlTests(unittest.TestCase):
    def test_uses_configured_client_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            Path(temporary_directory, ".env").write_text("CLIENT_ID=app_test\n")
            with patch("pathlib.Path.cwd", return_value=Path(temporary_directory)):
                url = CodexProvider().authorize_url(
                    "http://localhost:1455/auth/callback",
                    Pkce(verifier="verifier", challenge="challenge"),
                    "state",
                )

        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["client_id"], ["app_test"])


if __name__ == "__main__":
    unittest.main()
