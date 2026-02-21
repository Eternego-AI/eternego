"""Crypto — key derivation, encryption, and hashing."""

import hashlib
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


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


def sha256(data) -> str:
    """Return the SHA-256 hex digest of any data."""
    if not isinstance(data, (bytes, bytearray)):
        data = str(data).encode()
    return hashlib.sha256(data).hexdigest()


def generate_unique_id(content: str) -> str:
    """Generate a short unique hash from content."""
    return sha256(content)[:6]
