# Codex

[Back to the README](../../README.md)

Codex offers ChatGPT sign-in for subscription access and API-key sign-in for
usage-based access.

ratpass currently implements ChatGPT browser login and OAuth token refresh.

API-key authentication and headless device-code login are not implemented yet

## 1. ChatGPT account

Use a ChatGPT account with access to Codex.

### Get the client ID from Codex

With the Codex CLI installed, run:

```sh
codex login
```

Copy the `client_id` query parameter from the authorization URL printed in the
terminal or opened in your browser. For example, given:

```text
https://auth.openai.com/oauth/authorize?response_type=code&client_id=your_client_id_here&redirect_uri=...
```

copy only the value of `client_id`. The URL above is illustrative; use the value
from your actual login URL.

Stop the CLI login with Ctrl+C after copying the value, before starting ratpass,
to release the local callback port. You do not need to finish the CLI login.

### Configure ratpass

Create a `.env` file in the directory from which you will run Python:

```dotenv
CLIENT_ID=your_client_id_here
```

You can also pass the client ID directly, which takes precedence over `.env`:

```python
from ratpass.providers import CodexProvider

provider = CodexProvider(client_id="your_client_id_here")
```

### Sign in through the browser

```python
from ratpass.session import Session

session = Session.login("codex")
creds = session.credentials
```

Successful login saves the credentials to `~/.ratpass/credentials/codex.json`.
To reuse them in another process:

```python
from ratpass.session import Session

session = Session.load("codex")
if session is not None:
    creds = session.refresh()
```

Refresh automatically saves the updated tokens to the same file. Storage uses
plaintext JSON with owner-only file permissions on POSIX systems.

For explicit storage operations, use `save(credential)` and `load("codex")` from
`ratpass.storage`. Both accept an optional `directory` keyword argument. Sessions use the default directory shown above.
Direct provider login and refresh return credentials without saving them.

### Use the OpenAI Python client

Install the `openai` package separately; RatPass does not require it at runtime.
The session supplies the access token and Codex base URL:

```python
import os
import time

from openai import OpenAI
from ratpass.session import Session

session = Session.load("codex")
if session is None:
    session = Session.login("codex")

# Credential expiry is stored in milliseconds. Refresh explicitly when needed.
if session.credentials.expires <= (time.time() + 60) * 1000:
    session.refresh()

with OpenAI(**session.openai_options, timeout=120, max_retries=0) as client:
    with client.responses.create(
        model=os.environ["OPENAI_TEST_MODEL"],  # Set to a model your account can use.
        instructions="Answer briefly.",
        input=[{"role": "user", "content": "What is the capital of France?"}],
        store=False,
        stream=True,
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                print(event.delta, end="", flush=True)
            elif event.type in {"error", "response.failed", "response.incomplete"}:
                raise RuntimeError(f"Response stream ended with {event.type}")
    print()
```

`session.openai_options` returns `api_key` and `base_url`, with the endpoint
`https://chatgpt.com/backend-api/codex` defined by `CodexProvider`. Timeouts and
retries remain caller options. Accessing this property does not refresh tokens, save
credentials, or make network requests.

Options are a snapshot of the current credentials. After `session.refresh()`,
create a new client with fresh options; existing clients retain the old token.

This example follows the streaming Responses API usage in the repository's
[opt-in live tests](../../tests/live/test_openai.py), which also cover conversation
history, image input, structured output, and tool calls. The helper configures
the client; it does not establish support for every OpenAI SDK endpoint.
