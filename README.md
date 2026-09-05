# ratpass

Create a `.env` file in the project root. Its first value is the OAuth client
ID:

```dotenv
CLIENT_ID=app_EMoamEEZ73f0CkXaXp7hrann
```

RatPass loads this file automatically.

Use the Codex provider directly for browser or headless device authorization:

```python
from ratpass.providers import CodexProvider

provider = CodexProvider()
credential = provider.auth()  # opens the browser login
# credential = provider.auth(headless=True)  # prints a device code instead
```

`provider.refresh(credential.refresh)` renews an expired access token. The
returned credential's `expires` value is a Unix timestamp in milliseconds.

## Getting the client ID from Codex

Run:

```sh
codex login
```

Codex starts its local login server and prints an OpenAI authorization URL.
Copy the value of the URL's `client_id` query parameter. For example, in:

```text
https://auth.openai.com/oauth/authorize?response_type=code&client_id=app_example&redirect_uri=...
```

the client ID is `app_example`. You can press Ctrl+C after copying it if you do
not need to finish the login. The client ID is public OAuth application
metadata, not an access token or client secret. It can change between Codex
versions, so repeat this process after an authentication-related Codex update
if login stops working.

RatPass stores its local credential data at `~/.ratpass/credentials` by
default. The OAuth callback server uses the fixed port `1455`.

The directory is created with mode `0700` and the credentials file with mode
`0600` on Linux and macOS. The persistence layer does not encrypt values; data
that must be secret at rest should be encrypted before it is saved.
