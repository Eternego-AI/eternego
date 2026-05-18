"""Abilities — registry filtering and look_at behavior.

look_at is now always available — without a dedicated vision model it
falls back to the thinking model as eye. The `requires` predicate
framework still exists for future abilities that genuinely depend on
a capability; this test file no longer covers it because no production
ability currently uses it.
"""

from application.platform.processes import on_separate_process_async


async def test_look_at_available_with_or_without_vision():
    """look_at shows up in the registry for every persona, regardless of
    whether a dedicated vision model is configured."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            without_vision = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            with_vision = Persona(
                id="t", name="T",
                thinking=Model(name="m", url="not used"),
                vision=Model(name="v", url="not used"),
            )

            names_without = {a.name for a in abilities.available(without_vision)}
            names_with = {a.name for a in abilities.available(with_vision)}

            assert "look_at" in names_without
            assert "look_at" in names_with
            assert "save_notes" in names_without
            assert "save_notes" in names_with

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_document_lists_every_available_ability():
    """document(persona) renders every available ability, including look_at."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            without_vision = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            doc = abilities.document(without_vision)
            assert "save_notes" in doc
            assert "look_at" in doc

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_look_at_raises_when_source_missing_or_file_absent():
    """The ability raises ValueError on missing source or non-existent file —
    clock's executor wraps the exception into a TOOL_RESULT with status=error."""
    def isolated():
        import asyncio, os, tempfile
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            persona = Persona(
                id="t", name="T",
                thinking=Model(name="m", url="not used"),
                vision=Model(name="v", url="not used"),
            )
            living = SimpleNamespace(ego=SimpleNamespace(persona=persona), view={})
            try:
                asyncio.run(abilities.call(living, "look_at", source=""))
                assert False, "expected ValueError for empty source"
            except ValueError as e:
                assert "source is required" in str(e)
            try:
                asyncio.run(abilities.call(living, "look_at", source="/no/such/image.png"))
                assert False, "expected ValueError for missing file"
            except ValueError as e:
                assert "image not found" in str(e)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_actions_skip_variadic_abilities():
    """Abilities with `**kwargs` (the `screen` dispatcher pattern) can't
    be typed for strict-mode schemas — their args are open. `actions()`
    must skip them so the schema stays closed; the persona reaches the
    same capability via the underlying typed tools the variadic ability
    forwards to."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            names = {a.name for a in abilities.actions(persona)}
            # `screen` has `**args` → must be excluded
            assert "tools.screen" not in names, names
            # `save_notes` has typed params → must be present
            assert "tools.save_notes" in names, names
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_var_keyword_params_excluded_from_schema():
    """`**kwargs` (VAR_KEYWORD) must not appear in `Ability.params`. The
    `screen` ability uses `**args` to forward the desktop verb's kwargs;
    leaking that as a literal `args` key in the schema misled the persona
    into passing `args="<json>"` and the desktop verb rejected it."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities

            screen = next(a for a in abilities._registry if a.name == "screen")
            assert "action" in screen.params
            assert "args" not in screen.params
            assert "kwargs" not in screen.params

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_look_at_returns_media_with_question():
    """look_at no longer talks to the eye directly — it returns a Media
    carrying the persona's question. Realize on the next cycle is the
    place that actually asks the eye."""
    def isolated():
        import asyncio, os, tempfile
        from pathlib import Path
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Media, Model, Persona

            image_path = Path(tmp) / "shot.png"
            image_path.write_bytes(b"\x89PNG fake")

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            living = SimpleNamespace(ego=SimpleNamespace(persona=persona), view={})
            result = asyncio.run(abilities.call(
                living, "look_at",
                source=str(image_path),
                question="what color?",
            ))
            assert isinstance(result, Media)
            assert result.source == str(image_path)
            assert result.question == "what color?"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
