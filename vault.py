"""Encrypted local persistence for QuickVault."""
import base64
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Vault:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'QuickVault' / 'vault.json'
        self.cipher = None
        self.salt = None
        self.entries = []

    def unlock(self, password):
        exists = self.path.exists()
        document = json.loads(self.path.read_text('utf-8')) if exists else None
        salt = base64.b64decode(document['salt']) if exists else os.urandom(16)
        key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000).derive(password.encode('utf-8'))
        cipher = Fernet(base64.urlsafe_b64encode(key))
        entries = json.loads(cipher.decrypt(document['data'].encode())) if exists else []
        self.salt, self.cipher, self.entries = salt, cipher, entries
        if not exists:
            self.save()

    def save(self):
        if self.cipher is None:
            raise RuntimeError('Vault is locked')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {'version': 1, 'salt': base64.b64encode(self.salt).decode(), 'data': self.cipher.encrypt(json.dumps(self.entries).encode()).decode()}
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data), encoding='utf-8')
        os.replace(temporary, self.path)

    def lock(self):
        self.entries = []
        self.cipher = None
        self.salt = None
