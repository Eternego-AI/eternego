"""Meaning — abstract base class for all meanings."""

from abc import ABC, abstractmethod


class Meaning(ABC):
    name: str  # class-level identifier used for matching

    def __init__(self, persona):
        self.persona = persona

    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def clarification(self) -> str: ...

    @abstractmethod
    def reply(self) -> str: ...

    @abstractmethod
    def path(self) -> str | None: ...

    @abstractmethod
    async def run(self, persona_response: dict): ...
