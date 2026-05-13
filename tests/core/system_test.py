from application.core.system import persona_key, generate_recovery_phrases


def test_generate_recovery_phrases_returns_24_words():
    phrase = generate_recovery_phrases()
    words = phrase.split(" ")
    assert len(words) == 24


async def test_persona_key_derives_consistent_key():
    key1 = await persona_key("my phrase", "persona-1")
    key2 = await persona_key("my phrase", "persona-1")
    assert key1 == key2


async def test_persona_key_different_for_different_personas():
    key1 = await persona_key("my phrase", "persona-1")
    key2 = await persona_key("my phrase", "persona-2")
    assert key1 != key2
