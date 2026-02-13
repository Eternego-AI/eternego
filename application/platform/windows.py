"""Windows — Windows-specific shell operations and secure storage."""

import shutil


async def is_installed(program: str) -> bool:
    """Check if a program is installed on Windows."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on Windows."""
    if program == "ollama":
        raise NotImplementedError("Please install Ollama from ollama.com")
    elif program == "git":
        raise NotImplementedError("Please install Git from git-scm.com")


async def execute_on_sub_process(command: str) -> tuple[int, str]:
    """Execute a command on Windows via PowerShell and return (return_code, output)."""
    import asyncio

    process = await asyncio.create_subprocess_exec(
        "powershell", "-Command", command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode() if process.returncode == 0 else stderr.decode()
    return process.returncode, output.strip()


async def store_secret(key: str, value: str) -> None:
    """Store a secret in the Windows Credential Manager."""
    import win32crypt

    credential = {
        "Type": 1,  # CRED_TYPE_GENERIC
        "TargetName": f"eternego:{key}",
        "UserName": "eternego",
        "CredentialBlob": value,
        "Persist": 2,  # CRED_PERSIST_LOCAL_MACHINE
    }
    win32crypt.CredWrite(credential)


async def retrieve_secret(key: str) -> str:
    """Retrieve a secret from the Windows Credential Manager."""
    import win32crypt

    credential = win32crypt.CredRead(f"eternego:{key}", 1)
    return credential["CredentialBlob"].decode()
