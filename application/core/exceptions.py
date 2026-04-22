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

    `raw` carries the model's actual text so the caller can feed it back as the
    assistant turn, honest about what was produced.
    """

    def __init__(self, message: str = "", raw: str = ""):
        super().__init__(message)
        self.raw = raw


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


class BrainException(Exception):
    """The thinking model refused to cooperate even after a recovery attempt.

    Raised from cognitive steps (today: recognize) when the model produces
    prose instead of the required structured output AND a prior forced-recovery
    already happened this cycle-chain (e.g., meaning was already set to
    `troubleshooting` and the model still refused).

    Carries the `model` being used so tick can log a fault attributed to the
    thinking provider; health_check then marks the persona sick on the next
    heartbeat.
    """

    def __init__(self, message: str = "", model=None):
        super().__init__(message)
        self.model = model


class AgentError(Exception):
    pass
