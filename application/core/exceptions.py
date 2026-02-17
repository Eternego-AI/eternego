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


class PersonError(Exception):
    pass


class ExternalDataError(Exception):
    pass


class FrontierError(Exception):
    pass


class ExecutionError(Exception):
    pass


class DNAError(Exception):
    pass


class ChannelError(Exception):
    pass
