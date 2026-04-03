import os
import tempfile
from pathlib import Path

from application.core.brain.character import shape
from application.core.data import Model, Persona


def _with_temp_home(fn):
    """Run fn with a temporary HOME directory so paths resolve to temp."""
    original = os.environ.get("HOME")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HOME"] = tmp
        try:
            fn(Path(tmp))
        finally:
            if original:
                os.environ["HOME"] = original


def test_shape_composes_full_character_prompt():
    def run(tmp):
        persona = Persona(
            id="test-char",
            name="Primus",
            model=Model(name="llama3"),
            birthday="2026-01-15",
        )

        home = tmp / ".eternego" / "personas" / persona.id / "home"
        home.mkdir(parents=True)
        (home / "person.md").write_text("The person lives in Amsterdam.\nThe person is a software engineer.")
        (home / "persona-trait.md").write_text("Be concise.\nUse humor when appropriate.")

        result = shape(persona)

        assert "Primus" in result
        assert "2026-01-15" in result
        assert "Integrity" in result
        assert "Speak plainly" in result
        assert "Amsterdam" in result
        assert "Be concise" in result
        assert "# Who You Are" in result
        assert "# The Person You Live With" in result
        assert "# Your Personality" in result

    _with_temp_home(run)


def test_shape_omits_empty_identity_sections():
    def run(tmp):
        persona = Persona(
            id="test-empty",
            name="Primus",
            model=Model(name="llama3"),
        )

        home = tmp / ".eternego" / "personas" / persona.id / "home"
        home.mkdir(parents=True)
        (home / "person.md").write_text("")
        (home / "persona-trait.md").write_text("")

        result = shape(persona)

        assert "# Who You Are" in result
        assert "# The Person You Live With" not in result
        assert "# Your Personality" not in result

    _with_temp_home(run)
