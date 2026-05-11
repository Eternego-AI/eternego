"""Abilities — registry filtering and look_at behavior.

The registry filters abilities by their `requires` predicate. `look_at`
requires `persona.vision is not None`, so it shows up in the prompt and is
callable only for personas that have a vision model configured.
"""

from application.platform.processes import on_separate_process_async


async def test_available_filters_by_requires_predicate():
    """available(persona) excludes look_at when persona has no vision model,
    includes it when vision is configured."""
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

            assert "look_at" not in names_without
            assert "look_at" in names_with
            # other always-available abilities show in both
            assert "save_notes" in names_without
            assert "save_notes" in names_with

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_document_omits_unavailable_abilities():
    """document(persona) renders only available abilities. The line for
    look_at is absent for personas without vision."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            without_vision = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            doc = abilities.document(without_vision)
            assert "save_notes" in doc
            assert "look_at" not in doc

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_refuses_unavailable_ability():
    """call(persona, 'look_at', ...) raises ValueError when requires returns
    False — defense in depth even if the prompt didn't list it."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            try:
                asyncio.run(abilities.call(persona, "look_at", source="/x.png"))
                assert False, "expected ValueError"
            except ValueError as e:
                assert "not available" in str(e)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_look_at_raises_when_source_missing_or_file_absent():
    """The ability raises ValueError on missing source or non-existent file —
    clock's executor wraps the exception into a TOOL_RESULT with status=error."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            persona = Persona(
                id="t", name="T",
                thinking=Model(name="m", url="not used"),
                vision=Model(name="v", url="not used"),
            )
            try:
                asyncio.run(abilities.call(persona, "look_at", source=""))
                assert False, "expected ValueError for empty source"
            except ValueError as e:
                assert "source is required" in str(e)
            try:
                asyncio.run(abilities.call(persona, "look_at", source="/no/such/image.png"))
                assert False, "expected ValueError for missing file"
            except ValueError as e:
                assert "image not found" in str(e)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_report_dispatches_say_command():
    """`report` dispatches a 'Persona wants to say' Command — same dispatch as
    `say`, but called from inside a procedure (steps[]) to narrate progress
    while the beat continues."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona
            from application.platform import observer

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))

            captured = []
            async def capture(cmd: observer.Command):
                if cmd.title == "Persona wants to say":
                    captured.append(cmd.details.get("text", ""))
            observer.subscribe(capture)

            async def run_it():
                result = await abilities.call(persona, "report", text="halfway through")
                await asyncio.sleep(0)
                assert result == "reported", result
                assert captured == ["halfway through"], captured
            asyncio.run(run_it())

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_report_requires_text():
    """Empty text is a programmer error — the ability raises ValueError so
    the clock executor wraps it into a TOOL_RESULT with status=error."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            try:
                asyncio.run(abilities.call(persona, "report", text=""))
                assert False, "expected ValueError"
            except ValueError as e:
                assert "text is required" in str(e)

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


async def test_look_at_returns_eye_answer_for_real_image():
    """When source is valid and vision is configured, look_at calls the eye
    and returns its description as the ability's string result."""
    def isolated():
        import os, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import abilities
            from application.core.data import Model, Persona
            from application.platform import ollama

            image_path = Path(tmp) / "shot.png"
            image_path.write_bytes(b"\x89PNG fake")

            async def consume(url):
                persona = Persona(
                    id="t", name="T",
                    thinking=Model(name="m", url=url),
                    vision=Model(name="v", url=url),
                )
                result = await abilities.call(
                    persona, "look_at",
                    source=str(image_path),
                    question="what color?",
                )
                assert result == "a small green square"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "a small green square"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
