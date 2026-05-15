"""Learn stage — integration tests over a real Living.

Each test constructs a Living (Ego/Eye/Consultant/Teacher + Pulse with no-op
worker), seeds memory with a pending intention via `memory.intention()`
(the gate condition), calls `learn(living)`, and asserts on the impression
learn records back.

Learn fires only when `memory.perception()` returns an intention text.
On match against the catalog: records the meaning's body as the impression.
On miss: consults teacher, has the persona translate, saves both lesson and
meaning to disk, records the translated body as the impression. No
consequences emitted — cognitive function, no cycle restart.
"""

from application.platform.processes import on_separate_process_async


async def test_learn_skips_when_no_pending_call():
    """Without a pending `tools.load_instruction` call as the last signal,
    learn passes through immediately — no model call, no consequences, no
    memory mutation."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))

            msgs_before = len(living.memory.messages)
            consequences = asyncio.run(functions.learn(living))
            assert consequences == []
            assert len(living.memory.messages) == msgs_before

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_skips_when_last_signal_is_result():
    """If the last signal is already a TOOL_RESULT (the round-trip is complete),
    learn skips so decide can act on it."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.memory.intention("chatting")
            living.memory.impression("talk simply")

            msgs_before = len(living.memory.messages)
            consequences = asyncio.run(functions.learn(living))
            assert consequences == []
            assert len(living.memory.messages) == msgs_before

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_matches_existing_intention():
    """When the pending call's intention matches an existing meaning's
    intention text, learn writes the meaning's body as the matching
    TOOL_RESULT — no teacher call."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
            from application.core.brain import functions, meanings
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            # Plant a custom meaning the persona will reach for.
            living.memory.learn("posting_to_x", meanings.Meaning("posting_to_x", "Posting To X", "Draft. Ask. Post."))
            living.memory.intention("Posting To X")

            consequences = asyncio.run(functions.learn(living))
            assert consequences == []

            # Last message is the TOOL_RESULT carrying the meaning's body.
            last = living.memory.messages[-1]
            assert "TOOL_RESULT" in last.content
            assert "tool: load_instruction" in last.content
            assert "status: ok" in last.content
            assert "Draft. Ask. Post." in last.content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_consults_teacher_on_no_match():
    """When no meaning matches the intention, learn consults the teacher,
    has the persona translate the lesson, saves both, and writes the
    translated body as the matching TOOL_RESULT."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="t", name="T",
                    thinking=Model(name="m", url=url),
                    frontier=Model(name="m", url=url),
                )
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.intention("Checking disk space")

                consequences = await functions.learn(living)
                assert consequences == []

                # Teacher → translate produces a saved lesson and meaning.
                # File names are opaque UUIDs; look up via learned.json.
                learned = paths.read_json(paths.learned(persona.id)) or {}
                assert "Checking disk space" in learned, f"learned.json missing intention: {learned!r}"
                file_id = learned["Checking disk space"]
                lesson_file = paths.lessons(persona.id) / f"{file_id}.md"
                meaning_file = paths.meanings(persona.id) / f"{file_id}.md"
                assert lesson_file.exists(), f"lesson should be saved at {lesson_file}"
                assert meaning_file.exists(), f"meaning should be saved at {meaning_file}"
                assert file_id in living.memory.custom_meanings
                assert "df -h" in meaning_file.read_text()

                # Last message is the TOOL_RESULT with the translated body.
                last = living.memory.messages[-1]
                assert "TOOL_RESULT" in last.content
                assert "tool: load_instruction" in last.content
                assert "status: ok" in last.content
                assert "df -h" in last.content

            teacher_response = json.dumps({
                "intention": "Checking disk space",
                "path": "Disk space sits behind the operating system's disk-free utility — `df` on Unix.",
            })
            translation_response = "When asked, run df -h and tell them what's left."
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": teacher_response}, "done": True}],
                    [{"message": {"content": translation_response}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_teacher_falls_back_to_thinking_when_no_frontier():
    """Without a frontier configured, teacher uses the persona's thinking
    model. Learn still consults it and creates a meaning."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                # thinking is set, frontier is None — teacher.model falls back.
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                assert teacher.model is persona.thinking, "teacher must fall back to thinking"
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.intention("Greeting the person")

                consequences = await functions.learn(living)
                assert consequences == []
                assert paths.learned(persona.id).exists()

                # TOOL_RESULT got written.
                last = living.memory.messages[-1]
                assert "TOOL_RESULT" in last.content
                assert "status: ok" in last.content

            teacher_response = json.dumps({
                "intention": "Greeting the person",
                "path": "Return the greeting in your own voice.",
            })
            translation_response = "When the person says hello, say hello back warmly."
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": teacher_response}, "done": True}],
                    [{"message": {"content": translation_response}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_records_failure_impression_when_lesson_missing_fields():
    """Teacher returns a partial lesson (no path). Learn records a failure
    impression so the persona's next read sees that the round-trip closed
    without producing a usable procedure."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="t", name="T",
                    thinking=Model(name="m", url=url),
                    frontier=Model(name="m", url=url),
                )
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.intention("doing something")

                consequences = await functions.learn(living)
                assert consequences == []

                # Last message is the failure impression (round-trip closed).
                last = living.memory.messages[-1]
                assert "TOOL_RESULT" in last.content
                assert "could not produce a procedure" in last.content

            partial = json.dumps({"intention": "doing something", "path": ""})
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": partial}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_records_failure_impression_when_teacher_invalid_json():
    """Teacher returns prose — extract_json fails. Learn catches the
    ModelError, records a failure impression to close the exchange."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="t", name="T",
                    thinking=Model(name="m", url=url),
                    frontier=Model(name="m", url=url),
                )
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.intention("something")

                consequences = await functions.learn(living)
                assert consequences == []

                last = living.memory.messages[-1]
                assert "TOOL_RESULT" in last.content
                assert "could not produce a procedure" in last.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "I don't know how to design this"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_skips_when_intention_is_empty():
    """A `tools.load_instruction` call with empty `intention` — perception()
    returns None (empty strings filtered), so learn skips cleanly. The
    dangling call sits in memory but doesn't loop the cycle."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            # Manually plant an empty-intention call (intention() filters
            # empty strings, so we write the wire shape directly).
            empty = '{"tools.load_instruction": {}}'
            living.memory.remember(Message(content=empty, prompt=Prompt(role="assistant", content=empty)))

            msgs_before = len(living.memory.messages)
            consequences = asyncio.run(functions.learn(living))
            assert consequences == []
            assert len(living.memory.messages) == msgs_before, "learn should skip without writing"
            assert living.memory.perception() is None, "empty intention surfaces as None"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
