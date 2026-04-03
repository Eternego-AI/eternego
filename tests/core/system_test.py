import asyncio

from application.core.system import make_rows_traceable, persona_key, generate_recovery_phrases
from application.platform.crypto import generate_unique_id


def test_make_rows_traceable_tags_with_hash():
    rows = ["buy milk", "call dentist"]
    result = make_rows_traceable(rows, "todo")
    assert len(result) == 2
    assert result[0]["content"] == "buy milk"
    assert result[0]["id"] == f"todo-{generate_unique_id('buy milk')}"
    assert result[1]["id"].startswith("todo-")


def test_make_rows_traceable_empty_list():
    result = make_rows_traceable([], "prefix")
    assert result == []


def test_generate_recovery_phrases_returns_24_words():
    phrase = generate_recovery_phrases()
    words = phrase.split(" ")
    assert len(words) == 24


def test_persona_key_derives_consistent_key():
    key1 = asyncio.run(persona_key("my phrase", "persona-1"))
    key2 = asyncio.run(persona_key("my phrase", "persona-1"))
    assert key1 == key2


def test_persona_key_different_for_different_personas():
    key1 = asyncio.run(persona_key("my phrase", "persona-1"))
    key2 = asyncio.run(persona_key("my phrase", "persona-2"))
    assert key1 != key2
