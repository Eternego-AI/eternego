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


async def test_reflect_in_morning_phase_skips():
    """Morning is for waking and starting, not for reflection. Reflect
    never runs during MORNING phase, regardless of memory or idle state."""
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
            living.pulse.phase = Phase.MORNING
            # Even with messages and an idle-True monkey-patch, reflect skips.
            ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
            async def _idle(*a, **kw): return True
            living.is_idle = _idle

            identity_file = paths.person_identity(persona.id)
            assert not identity_file.exists()

            consequences = asyncio.run(functions.reflect(living))
            assert consequences == []

            # Messages untouched; no consolidation happened.
            assert len(ego.memory.messages) == 1
            assert not identity_file.exists()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_during_day_when_not_idle_raises_interrupted():
    """During the day, when is_idle reports False (a nudge cancelled the wait
    — activity arrived), reflect raises ReflectInterrupted so clock restarts
    the cycle from realize. Messages stay; person files unchanged."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.core.exceptions import ReflectInterrupted

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

            try:
                asyncio.run(functions.reflect(living))
                assert False, "reflect should have raised ReflectInterrupted"
            except ReflectInterrupted:
                pass

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


async def test_reflect_at_night_refines_and_creates_instructions():
    """At night, reflect first asks the persona to update instructions based
    on today's lived experience (refine existing, create new, delete stale),
    then calls consolidate. Two model calls: one for instruction updates,
    one for long-term files."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions, meanings
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                # Seed a custom meaning the persona may want to refine.
                paths.save_as_string(paths.meanings(persona.id) / "asking_for_keys.md", "Old vague body.\n")
                paths.save_as_json(persona.id, paths.learned(persona.id), {"asking for keys": "asking_for_keys"})

                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                living.pulse.phase = Phase.NIGHT
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))

                consequences = await functions.reflect(living)
                assert consequences == []

                # Refined body persisted at the existing file (matched via
                # learned.json lookup; file_id stays `asking_for_keys`).
                refined_body = paths.read(paths.meanings(persona.id) / "asking_for_keys.md")
                assert "specific updated body" in refined_body
                assert "Old vague body" not in refined_body

                # learned.json: refine kept existing file_id; new entry was
                # written under a fresh UUID for the new intention.
                learned = paths.read_json(paths.learned(persona.id)) or {}
                assert learned.get("asking for keys") == "asking_for_keys"
                assert "publishing via PR" in learned, f"new intention missing: {learned!r}"
                new_file_id = learned["publishing via PR"]

                # New meaning file exists under the UUID, only in meanings/
                # (no lesson side-effect — persona-authored procedures don't
                # produce separate teacher lessons).
                new_meaning = paths.meanings(persona.id) / f"{new_file_id}.md"
                assert new_meaning.exists()
                assert "gh pr create" in new_meaning.read_text()
                assert not (paths.lessons(persona.id) / f"{new_file_id}.md").exists(), \
                    "reflect.new should not write to lessons/"

                # Long-term consolidation also happened.
                assert paths.person_identity(persona.id).exists()
                assert ego.memory.messages == []

            # Refine matches by intention text ("asking for keys"), not stem.
            updates = json.dumps({
                "updates": [
                    {"refine": "asking for keys", "path": "specific updated body with steps"},
                    {"new": True, "intention": "publishing via PR", "path": "Run gh pr create with the right base and head."},
                ]
            })
            consolidation = json.dumps({
                "context": "today closed",
                "identity": ["A"],
                "traits": [], "wishes": [], "struggles": [],
                "persona_traits": [], "permissions": [],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": updates}, "done": True}],
                    [{"message": {"content": consolidation}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_at_night_empty_updates_still_consolidates():
    """If reflect's instruction-update returns an empty list, consolidation
    still runs. Reflect makes two model calls regardless: instruction updates,
    then long-term consolidation."""
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
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))

                consequences = await functions.reflect(living)
                assert consequences == []
                # Consolidation still ran — context written.
                assert ego.memory.context == "quiet day"

            empty_updates = json.dumps({"updates": []})
            consolidation = json.dumps({
                "context": "quiet day",
                "identity": [], "traits": [], "wishes": [], "struggles": [],
                "persona_traits": [], "permissions": [],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": empty_updates}, "done": True}],
                    [{"message": {"content": consolidation}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_new_with_existing_intention_updates_existing_file():
    """When reflect emits `new` with an intention that's already in the
    catalog, the existing file is updated in place (no orphan UUID file
    created). This prevents catalog bloat when the model mis-uses `new`
    instead of `refine`."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions, meanings
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                # Seed a meaning the persona already has.
                paths.save_as_string(paths.meanings(persona.id) / "existing-file-id.md", "Old body.\n")
                paths.save_as_json(persona.id, paths.learned(persona.id), {"X engagement": "existing-file-id"})

                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                living.pulse.phase = Phase.NIGHT
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))

                consequences = await functions.reflect(living)
                assert consequences == []

                # Existing file was updated in place.
                updated = paths.read(paths.meanings(persona.id) / "existing-file-id.md")
                assert "New body for X engagement" in updated
                assert "Old body" not in updated

                # learned.json still has exactly one entry for this intention.
                learned = paths.read_json(paths.learned(persona.id)) or {}
                assert learned == {"X engagement": "existing-file-id"}, f"got {learned!r}"

                # No orphan file was created (no other .md in meanings/).
                meaning_files = list(paths.meanings(persona.id).glob("*.md"))
                assert len(meaning_files) == 1, f"expected 1 meaning file, got {[f.name for f in meaning_files]}"

            updates = json.dumps({
                "updates": [
                    {"new": True, "intention": "X engagement", "path": "New body for X engagement"},
                ]
            })
            consolidation = json.dumps({
                "context": "today",
                "identity": [], "traits": [], "wishes": [], "struggles": [],
                "persona_traits": [], "permissions": [],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": updates}, "done": True}],
                    [{"message": {"content": consolidation}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_at_night_delete_unlearns_custom_instruction():
    """`{"delete": "<intention>"}` removes a custom instruction's file,
    drops it from learned.json, and unlearns it from memory."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions, meanings
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                paths.save_as_string(paths.meanings(persona.id) / "outdated.md", "stale procedure\n")
                paths.save_as_json(persona.id, paths.learned(persona.id), {"outdated thing": "outdated"})

                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                living.pulse.phase = Phase.NIGHT
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                # Force the seeded meaning into memory's custom catalog.
                ego.memory.learn("outdated", meanings.Meaning("outdated", "outdated thing", "stale procedure"))

                consequences = await functions.reflect(living)
                assert consequences == []

                # File deleted.
                assert not (paths.meanings(persona.id) / "outdated.md").exists()
                # learned.json no longer has the intention.
                learned = paths.read_json(paths.learned(persona.id)) or {}
                assert "outdated thing" not in learned
                # Memory's custom catalog forgot it.
                assert "outdated" not in ego.memory.custom_meanings

            updates = json.dumps({"updates": [{"delete": "outdated thing"}]})
            consolidation = json.dumps({
                "context": "pruned",
                "identity": [], "traits": [], "wishes": [], "struggles": [],
                "persona_traits": [], "permissions": [],
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": updates}, "done": True}],
                    [{"message": {"content": consolidation}, "done": True}],
                ],
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
