# ratpass

ratpass is a Python library for authenticating with AI providers and refreshing
OAuth credentials. It currently implements Codex browser login.

## Backends

This table describes support **in ratpass**. Subscription access means signing
in with a provider account; headless means a device-code flow without a local
browser callback.

| Backend | Headless login | Browser login | Subscription access | API key | Status |
| --- | --- | --- | --- | --- | --- |
| [Codex](docs/providers/codex.md) | Not implemented | Supported | Supported via ChatGPT | Not implemented | Available |
| Local | — | — | — | — | Not implemented |
| xAI | — | — | — | — | Not implemented |
| OpenRouter | — | — | — | — | Not implemented |
| OpenCode | — | — | — | — | Not implemented |

A dash means ratpass has no implementation for that backend yet.

## Installation

Requires Python 3.14 or newer. From the repository root, install with uv:

```sh
uv sync
```

Or install into your Python environment with pip:

```sh
python -m pip install -e .
```

## Quick start

Follow the [Codex setup guide](docs/providers/codex.md) to obtain a client ID,
then create `.env` in the directory where you will run your script:

```dotenv
CLIENT_ID=your_client_id_here
```

Save this as `login.py` and run it with `uv run python login.py` (or
`python login.py` if you installed with pip):

```python
from ratpass.session import Session

session = Session.login("codex")
creds = session.credentials
```


## Development

Install the test dependencies and run the suite:

```sh
uv sync --extra test
uv run pytest
```

### Testing AI SDK
```sh
RUN_OPENAI_TESTS=1 uv run --extra test pytest tests/live/ -v -s
```
