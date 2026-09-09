from unittest.mock import patch

import pytest

from ratpass.config import Config
from ratpass.providers import Providers
from ratpass.types import ProviderId


@pytest.mark.parametrize("provider_id", list(ProviderId))
def test_registered_provider_matches_persisted_identifier(
    provider_id: ProviderId,
) -> None:
    with patch(
        "ratpass.providers.codex.Config.from_dotenv", return_value=Config("app_test")
    ):
        provider = Providers.create_provider(provider_id.value)

    assert provider.method_id == provider_id.value
    assert isinstance(provider, Providers[provider_id.name].value)


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        Providers.create_provider("unknown")


@pytest.mark.parametrize("enum_class", [ProviderId, Providers])
def test_enum_member_cannot_be_reassigned(enum_class: type) -> None:
    with pytest.raises(AttributeError):
        setattr(enum_class, "CODEX", "changed")  # noqa: B010 - test runtime enforcement
