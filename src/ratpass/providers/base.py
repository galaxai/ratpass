"""Shared OAuth infrastructure and provider interface."""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

from ratpass.metadata import USER_AGENT
from ratpass.providers.types import Credential, Pkce

CALLBACK_PORT = 1455
DEFAULT_TIMEOUT = 600.0


class AuthorizationError(RuntimeError):
    """Raised when OAuth authorization cannot be completed."""


class HttpError(AuthorizationError):
    """An OAuth endpoint returned a non-success status."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


def _request(
    url: str,
    *,
    method: str,
    headers: Mapping[str, str],
    body: str | bytes | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Send an HTTP request and return its JSON-object response."""

    data = body.encode("utf-8") if isinstance(body, str) else body
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=dict(headers),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise HttpError(
            error.code,
            f"{method} {url} returned HTTP {error.code}"
            + (f": {detail}" if detail else ""),
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise AuthorizationError(f"Could not reach {url}: {error}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthorizationError(f"{url} returned invalid JSON") from error

    if not isinstance(payload, dict):
        raise AuthorizationError(f"{url} returned a non-object JSON response")
    return payload


def _base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce() -> Pkce:
    """Generate an RFC 7636 verifier and S256 challenge."""

    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    verifier = "".join(secrets.choice(chars) for _ in range(43))
    challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return Pkce(verifier=verifier, challenge=challenge)


def start_callback_server(
    handler: type[http.server.BaseHTTPRequestHandler] | Callable[..., Any],
    *,
    port: int = CALLBACK_PORT,
) -> tuple[http.server.HTTPServer, threading.Thread]:
    """Start a localhost OAuth callback server in a background thread."""

    server = http.server.HTTPServer(("localhost", port), handler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="ratpass-oauth-callback",
        daemon=True,
    )
    thread.start()
    return server, thread


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Capture an OAuth authorization response from a localhost redirect."""

    def __init__(
        self,
        *args: Any,
        expected_state: str,
        result: dict[str, str],
        done: threading.Event,
        **kwargs: Any,
    ) -> None:
        self.expected_state = expected_state
        self.result = result
        self.done = done
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        url = urllib.parse.urlparse(self.path)
        if url.path != "/auth/callback":
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(url.query)
        state = params.get("state", [None])[0]
        if state != self.expected_state:
            self._fail("Invalid OAuth state")
            return

        error = params.get("error", [None])[0]
        if error:
            self._fail(params.get("error_description", [error])[0])
            return

        code = params.get("code", [None])[0]
        if not code:
            self._fail("Missing authorization code")
            return

        self.result["code"] = code
        self._respond(200, "Authorization completed. You can close this page.")
        self.done.set()

    def _fail(self, message: str) -> None:
        self.result["error"] = message
        self._respond(400, message)
        self.done.set()

    def _respond(self, status: int, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class BaseProvider(ABC):
    """Base class for providers using OAuth authorization-code login."""

    def __init__(
        self,
        *,
        client_id: str,
        issuer: str,
        callback_port: int = CALLBACK_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = USER_AGENT,
    ) -> None:
        if not client_id:
            raise ValueError("client_id must not be empty")
        self.client_id = client_id
        self.issuer = issuer.rstrip("/")
        self.callback_port = callback_port
        self.timeout = timeout
        self.user_agent = user_agent

    @abstractmethod
    def authorize_url(self, redirect: str, pkce: Pkce, state: str) -> str:
        """Build the provider-specific authorization URL."""

    @abstractmethod
    def credential_from_tokens(self, tokens: Mapping[str, Any]) -> Credential:
        """Convert a provider token response into a credential."""

    @abstractmethod
    def headless_authorize(self) -> Credential:
        """Run the provider-specific headless authorization flow."""

    def exchange(self, code: str, redirect: str, pkce: Pkce) -> dict[str, Any]:
        """Exchange an authorization code for tokens."""

        return _request(
            f"{self.issuer}/oauth/token",
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
            body=urllib.parse.urlencode(
                {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "client_id": self.client_id,
                    "code_verifier": pkce.verifier,
                }
            ),
        )

    def browser_authorize(
        self,
        *,
        open_browser: bool = True,
        opener: Callable[[str], Any] = webbrowser.open,
    ) -> Credential:
        """Run the shared localhost browser authorization flow."""

        pkce = generate_pkce()
        state = _base64url(secrets.token_bytes(32))
        done = threading.Event()
        result: dict[str, str] = {}
        handler = partial(
            _CallbackHandler,
            expected_state=state,
            result=result,
            done=done,
        )
        server, thread = start_callback_server(handler, port=self.callback_port)
        redirect = f"http://localhost:{server.server_port}/auth/callback"

        try:
            url = self.authorize_url(redirect, pkce, state)
            print(f"Open this URL to authorize RatPass:\n{url}")
            if open_browser:
                opener(url)
            if not done.wait(timeout=self.timeout):
                raise TimeoutError("OAuth callback was not received before timeout")
            if "error" in result:
                raise AuthorizationError(result["error"])
            return self.credential_from_tokens(
                self.exchange(result["code"], redirect, pkce)
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def auth(self, *, headless: bool = False) -> Credential:
        """Run browser or headless authorization."""

        if headless:
            return self.headless_authorize()
        return self.browser_authorize()
