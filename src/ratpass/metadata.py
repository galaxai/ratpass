"""Package identity shared by RatPass integrations."""

from importlib.metadata import version

PROJECT_NAME = "ratpass"
PROJECT_VERSION = version(PROJECT_NAME)
USER_AGENT = f"{PROJECT_NAME}/{PROJECT_VERSION}"


if __name__ == "__main__":
    print(PROJECT_VERSION, USER_AGENT)
