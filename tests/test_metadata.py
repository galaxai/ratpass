from importlib.metadata import version

from ratpass.metadata import PROJECT_NAME, PROJECT_VERSION, USER_AGENT


def test_user_agent_uses_project_metadata() -> None:
    assert PROJECT_VERSION == version(PROJECT_NAME)
    assert USER_AGENT == f"{PROJECT_NAME}/{PROJECT_VERSION}"
