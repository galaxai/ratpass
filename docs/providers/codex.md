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
from ratpass.providers import CodexProvider

provider = CodexProvider()
credential = provider.auth()
```

Successful login saves the credentials to `~/.ratpass/credentials/codex.json`.
To reuse them in another process:

```python
from ratpass.storage import load
from ratpass.providers import CodexProvider

provider = CodexProvider()
credential = load("codex")
if credential is not None:
    credential = provider.refresh(credential.refresh)
```

Refresh automatically saves the updated tokens to the same file. Storage uses
plaintext JSON with owner-only file permissions on POSIX systems.

For explicit storage operations, use `save(credential)` and `load("codex")` from
`ratpass.storage`. Both accept an optional `directory` keyword argument; provider
login and refresh use the default directory shown above.
