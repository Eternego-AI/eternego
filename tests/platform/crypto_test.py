from application.platform.crypto import (
    decrypt,
    derive_key,
    encrypt,
    generate_unique_id,
    sha256,
)


async def test_it_hashes_strings_consistently():
    a = sha256("hello")
    b = sha256("hello")
    assert a == b


async def test_it_hashes_different_inputs_differently():
    assert sha256("hello") != sha256("world")


async def test_it_hashes_bytes_directly():
    result = sha256(b"hello")
    assert isinstance(result, str)
    assert len(result) == 64


async def test_it_generates_short_unique_ids():
    result = generate_unique_id("some content")
    assert len(result) == 6
    assert result == sha256("some content")[:6]


async def test_it_generates_different_ids_for_different_content():
    assert generate_unique_id("a") != generate_unique_id("b")


async def test_it_encrypts_and_decrypts_roundtrip():
    salt = b"0123456789abcdef"
    key = derive_key("my-secret", salt)
    original = b"sensitive data"
    encrypted = encrypt(original, key)
    decrypted = decrypt(encrypted, key)
    assert decrypted == original
    assert encrypted != original


async def test_it_derives_consistent_keys():
    salt = b"fixed-salt-value"
    a = derive_key("secret", salt)
    b = derive_key("secret", salt)
    assert a == b


async def test_it_derives_different_keys_for_different_secrets():
    salt = b"fixed-salt-value"
    a = derive_key("secret-1", salt)
    b = derive_key("secret-2", salt)
    assert a != b
