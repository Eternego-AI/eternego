"""Crypto — key derivation and encryption."""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64


def derive_key(secret: str, salt: bytes) -> bytes:
    """Derive an encryption key from a string using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt data using a Fernet key."""
    return Fernet(key).encrypt(data)


def decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt data using a Fernet key."""
    return Fernet(key).decrypt(data)
