import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ratpass.config import Config


class ConfigTests(unittest.TestCase):
    def test_client_id_is_loaded_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dotenv_path = Path(temporary_directory) / ".env"
            dotenv_path.write_text("CLIENT_ID=app_from_dotenv\n")
            with patch("pathlib.Path.cwd", return_value=Path(temporary_directory)):
                self.assertEqual(
                    Config.from_dotenv().client_id,
                    "app_from_dotenv",
                )


if __name__ == "__main__":
    unittest.main()
