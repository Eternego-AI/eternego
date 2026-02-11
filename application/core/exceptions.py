"""Exceptions for the application."""


class UnsupportedOS(Exception):
    pass


class InstallationError(Exception):
    pass


class EngineConnectionError(Exception):
    pass


class SecretStorageError(Exception):
    pass


class DiaryError(Exception):
    pass


class IdentityError(Exception):
    pass
