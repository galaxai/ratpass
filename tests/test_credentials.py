import tempfile
import unittest
from pathlib import Path

from ratpass.credentials import CredentialsError, CredentialStore


class CredentialStoreTests(unittest.TestCase):
    def test_missing_file_loads_as_empty_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CredentialStore(Path(directory) / "ratpass" / "credentials")
            self.assertEqual(store.load(), {})

    def test_round_trip_and_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ratpass" / "credentials"
            store = CredentialStore(path)

            store.save({"example": {"username": "rat", "password": "secret"}})

            self.assertEqual(
                store.load(),
                {"example": {"username": "rat", "password": "secret"}},
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_invalid_json_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials"
            path.write_text("not json", encoding="utf-8")

            with self.assertRaises(CredentialsError):
                CredentialStore(path).load()


if __name__ == "__main__":
    unittest.main()
