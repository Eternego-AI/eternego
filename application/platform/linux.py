"""Linux — Linux-specific shell operations and secure storage."""

import asyncio
import shutil


async def is_installed(program: str) -> bool:
    """Check if a program is installed on Linux."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on Linux."""
    if program == "ollama":
        process = await asyncio.create_subprocess_shell(
            "curl -fsSL https://ollama.com/install.sh | sh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
    elif program == "git":
        process = await asyncio.create_subprocess_exec(
            "sudo", "apt", "install", "-y", "git",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()


async def store_secret(key: str, value: str) -> None:
    """Store a secret in the Linux Secret Service (GNOME Keyring / KWallet)."""
    import secretstorage

    connection = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(connection)
    collection.create_item(f"eternego:{key}", {"application": "eternego", "key": key}, value.encode())


async def retrieve_secret(key: str) -> str:
    """Retrieve a secret from the Linux Secret Service."""
    import secretstorage

    connection = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(connection)
    for item in collection.get_all_items():
        if item.get_label() == f"eternego:{key}":
            return item.get_secret().decode()
    raise KeyError(f"Secret not found: {key}")
