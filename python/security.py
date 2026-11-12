from pathlib import Path
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parents[1]
KEY_PATH = BASE_DIR / "python" / ".fernet_key"

def _load_or_create_key() -> bytes:
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()

    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    return key

_F = Fernet(_load_or_create_key())

def encrypt_text(text: str) -> str:
    return _F.encrypt(text.encode("utf-8")).decode("utf-8")

def decrypt_text(token: str) -> str:
    return _F.decrypt(token.encode("utf-8")).decode("utf-8")
