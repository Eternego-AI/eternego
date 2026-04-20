"""Exceptions for the application."""


class UnsupportedOS(Exception):
    pass


class InstallationError(Exception):
    pass


class EngineConnectionError(Exception):
    """The model service is unavailable or failed to produce any response.

    Raised for infrastructure-level failures — local engine down, OOM, remote API
    HTTP errors, rate limits, network outages, empty streams. Not recoverable by
    re-prompting the model: the caller should back off, not retry in a loop.

    `model` carries the Model that was being used when the fault happened, so
    health_check can correlate by provider (ollama/anthropic/openai).
    """

    def __init__(self, message: str = "", model=None):
        super().__init__(message)
        self.model = model


class ModelError(Exception):
    """The model responded, but the response's structure is not what we expected.

    Raised when JSON is malformed, missing expected keys, or otherwise unusable.
    Recoverable by letting the model see the error and try again on the next turn.
    """
    pass


class SecretStorageError(Exception):
    pass


class DiaryError(Exception):
    pass


class IdentityError(Exception):
    pass


class PersonError(Exception):
    pass


class FrontierError(Exception):
    pass


class ExecutionError(Exception):
    pass


class ChannelError(Exception):
    pass


class SkillError(Exception):
    pass


class HistoryError(Exception):
    pass


class ContextError(Exception):
    pass


class HardwareError(Exception):
    pass


class MindError(Exception):
    pass


class AgentError(Exception):
    pass
