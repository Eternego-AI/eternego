import os
import tempfile

from application.core.brain.mind import subconscious
from application.core import paths
from application.core.data import Model, Persona
from application.platform import ollama


_original_home = os.environ.get("HOME")


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp
    return tmp


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home


def _persona():
    p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
    paths.home(p.id).mkdir(parents=True, exist_ok=True)
    return p


# ── person_identity ──────────────────────────────────────────────────────────

def test_person_identity_writes_model_response_to_file():
    _setup()
    p = _persona()

    ollama.assert_call(
        run=lambda: subconscious.person_identity(p, "Person: I live in Amsterdam"),
        response={"message": {"content": "The person lives in Amsterdam."}},
    )

    content = paths.read(paths.person_identity(p.id))
    assert "Amsterdam" in content
    _teardown()


def test_person_identity_includes_existing_facts_in_prompt():
    _setup()
    p = _persona()
    paths.save_as_string(paths.person_identity(p.id), "The person is a developer.")

    ollama.assert_call(
        run=lambda: subconscious.person_identity(p, "Person: I moved to Paris"),
        validate=lambda r: assert_in("The person is a developer.", r["body"]["messages"][0]["content"]),
        response={"message": {"content": "The person is a developer.\nThe person lives in Paris."}},
    )
    _teardown()


def test_person_identity_sends_conversation_as_user_message():
    _setup()
    p = _persona()

    ollama.assert_call(
        run=lambda: subconscious.person_identity(p, "Person: My name is Morteza"),
        validate=lambda r: (
            _assert_equal(r["body"]["messages"][1]["role"], "user"),
            assert_in("Morteza", r["body"]["messages"][1]["content"]),
        ),
        response={"message": {"content": "The person's name is Morteza."}},
    )
    _teardown()


# ── person_traits ────────────────────────────────────────────────────────────

def test_person_traits_writes_to_correct_file():
    _setup()
    p = _persona()

    ollama.assert_call(
        run=lambda: subconscious.person_traits(p, "Person: just give me the answer"),
        response={"message": {"content": "The person prefers concise responses."}},
    )

    content = paths.read(paths.person_traits(p.id))
    assert "concise" in content
    _teardown()


def test_person_traits_includes_existing_in_prompt():
    _setup()
    p = _persona()
    paths.save_as_string(paths.person_traits(p.id), "The person uses humor.")

    ollama.assert_call(
        run=lambda: subconscious.person_traits(p, "Person: be brief"),
        validate=lambda r: assert_in("The person uses humor.", r["body"]["messages"][0]["content"]),
        response={"message": {"content": "The person uses humor.\nThe person prefers brevity."}},
    )
    _teardown()


# ── wishes ───────────────────────────────────────────────────────────────────

def test_wishes_writes_to_correct_file():
    _setup()
    p = _persona()

    ollama.assert_call(
        run=lambda: subconscious.wishes(p, "Person: I want to visit Japan"),
        response={"message": {"content": "The person wants to visit Japan."}},
    )

    content = paths.read(paths.wishes(p.id))
    assert "Japan" in content
    _teardown()


# ── struggles ────────────────────────────────────────────────────────────────

def test_struggles_writes_to_correct_file():
    _setup()
    p = _persona()

    ollama.assert_call(
        run=lambda: subconscious.struggles(p, "Person: I keep procrastinating"),
        response={"message": {"content": "The person struggles with procrastination."}},
    )

    content = paths.read(paths.struggles(p.id))
    assert "procrastination" in content
    _teardown()


# ── persona_trait ────────────────────────────────────────────────────────────

def test_persona_trait_writes_to_correct_file():
    _setup()
    p = _persona()

    ollama.assert_call(
        run=lambda: subconscious.persona_trait(p, "Person: don't give me filler"),
        response={"message": {"content": "Be concise and direct."}},
    )

    content = paths.read(paths.persona_trait(p.id))
    assert "concise" in content
    _teardown()


def test_persona_trait_includes_person_traits_in_prompt():
    _setup()
    p = _persona()
    paths.save_as_string(paths.person_traits(p.id), "The person is direct and technical.")

    ollama.assert_call(
        run=lambda: subconscious.persona_trait(p, "Person: use DDD"),
        validate=lambda r: assert_in("The person is direct and technical.", r["body"]["messages"][0]["content"]),
        response={"message": {"content": "Be direct.\nUse DDD terminology."}},
    )
    _teardown()


# ── synthesize_dna ───────────────────────────────────────────────────────────

def test_synthesize_dna_writes_to_dna_file():
    _setup()
    p = _persona()
    paths.save_as_string(paths.persona_trait(p.id), "Be concise.\nUse humor.")

    ollama.assert_call(
        run=lambda: subconscious.synthesize_dna(p),
        response={"message": {"content": "# Communication Style\n**Be concise**\nUse humor"}},
    )

    content = paths.read(paths.dna(p.id))
    assert "concise" in content
    assert "humor" in content
    _teardown()


def test_synthesize_dna_includes_previous_dna_and_traits_in_prompt():
    _setup()
    p = _persona()
    paths.save_as_string(paths.dna(p.id), "Previous profile content")
    paths.save_as_string(paths.persona_trait(p.id), "Be direct.")

    ollama.assert_call(
        run=lambda: subconscious.synthesize_dna(p),
        validate=lambda r: (
            assert_in("Previous profile content", r["body"]["messages"][0]["content"]),
            assert_in("Be direct.", r["body"]["messages"][0]["content"]),
        ),
        response={"message": {"content": "# Updated profile"}},
    )
    _teardown()


# ── Helpers ──────────────────────────────────────────────────────────────────

def assert_in(substring, text):
    assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"


def _assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
