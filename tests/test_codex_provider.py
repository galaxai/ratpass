import base64
import json
import unittest
import urllib.request
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse

from ratpass.metadata import PROJECT_NAME, USER_AGENT
from ratpass.providers.base import HttpError
from ratpass.providers.codex import CodexProvider
from ratpass.providers.types import Pkce


def _jwt(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    return f"header.{encoded.decode()}.signature"


class CodexProviderTests(unittest.TestCase):
    def test_authorize_url_contains_codex_parameters(self) -> None:
        provider = CodexProvider("app_test")
        url = provider.authorize_url(
            "http://localhost:1455/auth/callback",
            Pkce(verifier="secret", challenge="challenge"),
            "state",
        )

        self.assertEqual(urlparse(url).path, "/oauth/authorize")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["client_id"], ["app_test"])
        self.assertEqual(query["code_challenge"], ["challenge"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["state"], ["state"])
        self.assertEqual(query["originator"], [PROJECT_NAME])

    def test_exchange_sends_authorization_code_and_verifier(self) -> None:
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

        self.assertEqual(result, tokens)
        arguments = request.call_args.kwargs
        body = parse_qs(arguments["body"])
        self.assertEqual(body["code"], ["authorization-code"])
        self.assertEqual(body["code_verifier"], ["verifier"])
        self.assertEqual(body["client_id"], ["app_test"])
        self.assertEqual(arguments["headers"]["User-Agent"], USER_AGENT)

    def test_token_response_becomes_credential(self) -> None:
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

        self.assertEqual(credential.type, "oauth")
        self.assertEqual(credential.method_id, "codex")
        self.assertEqual(credential.access, "access")
        self.assertEqual(credential.refresh, "refresh")
        self.assertEqual(credential.expires, 160_000)
        self.assertEqual(
            credential.metadata,
            {"id_token": id_token, "account_id": "account-123"},
        )

    def test_browser_flow_receives_callback_and_returns_credential(self) -> None:
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
            callback += separator + urlencode(
                {"code": "code", "state": query["state"][0]}
            )
            with urllib.request.urlopen(callback, timeout=2) as response:
                self.assertEqual(response.status, 200)

        with patch.object(provider, "exchange", return_value=tokens) as exchange:
            credential = provider.browser_authorize(opener=complete_login)

        exchange.assert_called_once()
        self.assertEqual(credential.access, "access")

    def test_headless_flow_polls_and_exchanges_code(self) -> None:
        provider = CodexProvider("app_test")
        provider._sleep = lambda _seconds: None
        pending = HttpError(403, "pending")
        responses = [
            {"device_auth_id": "device-id", "user_code": "ABCD", "interval": "1"},
            pending,
            {"authorization_code": "code", "code_verifier": "verifier"},
        ]
        tokens = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }

        with (
            patch("ratpass.providers.codex._request", side_effect=responses) as request,
            patch.object(provider, "exchange", return_value=tokens) as exchange,
        ):
            credential = provider.headless_authorize()

        self.assertEqual(request.call_count, 3)
        exchange.assert_called_once_with(
            "code",
            "https://auth.openai.com/deviceauth/callback",
            Pkce(verifier="verifier", challenge=""),
        )
        self.assertEqual(credential.access, "access")

    def test_refresh_keeps_refresh_token_when_server_does_not_rotate_it(self) -> None:
        provider = CodexProvider("app_test")
        with patch(
            "ratpass.providers.codex._request",
            return_value={"access_token": "new-access", "expires_in": 60},
        ) as request:
            credential = provider.refresh("existing-refresh")

        body = parse_qs(request.call_args.kwargs["body"])
        self.assertEqual(body["grant_type"], ["refresh_token"])
        self.assertEqual(body["refresh_token"], ["existing-refresh"])
        self.assertEqual(credential.refresh, "existing-refresh")
        self.assertEqual(credential.access, "new-access")


if __name__ == "__main__":
    unittest.main()
