import tempfile
import unittest
from pathlib import Path
from cryptography.fernet import InvalidToken
from vault import Vault


class VaultTests(unittest.TestCase):
    def test_encrypted_roundtrip_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vault.json'
            vault = Vault(path)
            vault.unlock('a long test password')
            vault.entries = [{'title': 'Private title', 'content': 'sk-private-key', 'tags': 'private'}]
            vault.save()
            raw = path.read_text()
            self.assertNotIn('sk-private-key', raw)
            self.assertNotIn('Private title', raw)
            vault.lock()
            self.assertIsNone(vault.cipher)
            self.assertEqual(vault.entries, [])
            with self.assertRaises(InvalidToken):
                vault.unlock('incorrect password')
            vault.unlock('a long test password')
            self.assertEqual(vault.entries[0]['content'], 'sk-private-key')


if __name__ == '__main__':
    unittest.main()
