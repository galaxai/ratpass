import unittest
from importlib.metadata import version

from ratpass.metadata import PROJECT_NAME, PROJECT_VERSION, USER_AGENT


class MetadataTests(unittest.TestCase):
    def test_user_agent_uses_project_metadata(self) -> None:
        self.assertEqual(PROJECT_VERSION, version(PROJECT_NAME))
        self.assertEqual(USER_AGENT, f"{PROJECT_NAME}/{PROJECT_VERSION}")


if __name__ == "__main__":
    unittest.main()
