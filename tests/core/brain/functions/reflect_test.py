"""Reflect stage — integration tests over a real Living.

Reflect is the trigger; `consolidate(living)` is the actual work. Tests cover
both: reflect's gating (phase + idle), and consolidate's effects (file writes,
archive, forget) when the gate opens.
"""

from application.platform.processes import on_separate_process_async


async def test_reflect_no_messages_passes_through():
    """If memory has no messages there's nothing to consolidate. Returns []
    without a model call."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Model, Persona

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)

            consequences = asyncio.run(functions.reflect(living))
            assert consequences == []
            assert ego.memory.messages == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_during_day_when_not_idle_passes_through():
    """During the day, when is_idle reports False (a nudge cancelled the wait
    — activity arrived), reflect skips. Messages stay; person files unchanged."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.pulse.phase = Phase.DAY
            async def _not_idle(*a, **kw): return False
            living.is_idle = _not_idle
            ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))

            identity_file = paths.person_identity(persona.id)
            assert not identity_file.exists(), "test premise: identity file should not exist yet"

            consequences = asyncio.run(functions.reflect(living))
            assert consequences == []
            assert len(ego.memory.messages) == 1, "messages stay during the day"
            assert not identity_file.exists(), "no person file should be written"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_at_night_consolidates():
    """At night, reflect always consolidates. Person files get written and
    messages move into the archive."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                living.pulse.phase = Phase.NIGHT
                ego.memory.remember(Message(content="we talked about X", prompt=Prompt(role="user", content="we talked about X")))

                consequences = await functions.reflect(living)

                assert consequences == []
                assert ego.memory.messages == [], "messages should be archived after consolidate"
                assert len(ego.memory.archive) == 1, "one batch in archive"
                assert ego.memory.context == "we covered X today, easy"
                assert paths.person_identity(persona.id).read_text().strip() == "- Likes X"
                assert paths.persona_trait(persona.id).read_text().strip() == "- Be present"
                assert paths.permissions(persona.id).read_text().strip() == "- Allowed to use X"

            response = json.dumps({
                "context": "we covered X today, easy",
                "identity": ["Likes X"],
                "traits": [],
                "wishes": [],
                "struggles": [],
                "persona_traits": ["Be present"],
                "permissions": ["Allowed to use X"],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": response}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_when_idle_consolidates():
    """Even during the day, if the persona has been idle long enough, reflect
    consolidates. Tested by monkey-patching is_idle to True."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                living.pulse.phase = Phase.DAY
                async def _idle(*a, **kw): return True
                living.is_idle = _idle
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))

                consequences = await functions.reflect(living)

                assert consequences == []
                assert ego.memory.messages == [], "consolidated → archived → forgotten"
                assert paths.person_identity(persona.id).exists()

            response = json.dumps({
                "context": "drifted into stillness",
                "identity": ["Quiet"],
                "traits": [], "wishes": [], "struggles": [],
                "persona_traits": [], "permissions": [],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": response}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_consolidate_writes_person_files_and_archives():
    """Direct call to consolidate (no trigger gate) writes all six person files,
    sets context, archives messages, and forgets."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.functions.reflect import consolidate
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))

                changed = await consolidate(living)
                assert changed is True

                assert paths.person_identity(persona.id).read_text().strip() == "- A\n- B"
                assert paths.person_traits(persona.id).read_text().strip() == "- thoughtful"
                assert paths.wishes(persona.id).read_text().strip() == "- peace"
                assert paths.struggles(persona.id).read_text().strip() == "- noise"
                assert paths.persona_trait(persona.id).read_text().strip() == "- be quiet"
                assert paths.permissions(persona.id).read_text().strip() == "- yes"
                assert ego.memory.context == "first day together"
                assert ego.memory.messages == []
                assert len(ego.memory.archive) == 1

            response = json.dumps({
                "context": "first day together",
                "identity": ["A", "B"],
                "traits": ["thoughtful"],
                "wishes": ["peace"],
                "struggles": ["noise"],
                "persona_traits": ["be quiet"],
                "permissions": ["yes"],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": response}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_consolidate_handles_invalid_json():
    """ModelError → consolidate returns False, no files touched, messages stay
    so the next consolidation can retry from the same place."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.functions.reflect import consolidate
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                msgs_before = len(ego.memory.messages)

                changed = await consolidate(living)
                assert changed is False
                assert not paths.person_identity(persona.id).exists()
                assert len(ego.memory.messages) == msgs_before, "messages should remain on failure"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "no json here"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
