"""Learn stage — integration tests over a real Living.

Each test constructs a Living (Ego/Eye/Consultant/Teacher + Pulse with no-op
worker), seeds memory state to the precondition learn expects, calls
`learn(living)`, and asserts on returned consequences and memory state.

Teacher's only output is a lesson — `{"intention": "...", "path": "..."}`.
The persona's thinking model translates the lesson into a meaning. learn
saves both, links them in learned.json, and sets memory.meaning so decide
takes over on the same beat.
"""

from application.platform.processes import on_separate_process_async


async def test_learn_passes_when_meaning_already_set():
    """If recognize already chose a meaning (memory.meaning is set), learn passes
    through immediately — no model call, no consequences, no state change."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
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
            ego.memory.meaning = "chatting"
            ego.memory.impression = "doesn't matter"

            consequences = asyncio.run(functions.learn(living))
            assert consequences == []
            assert ego.memory.meaning == "chatting"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_passes_when_no_impression():
    """If recognize concluded the moment cleanly (say or done), no impression
    remains. Learn passes through silently — nothing to escalate."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(
                id="t", name="T",
                thinking=Model(name="m", url="not used"),
                frontier=Model(name="m", url="not used"),
            )
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            ego.memory.impression = ""

            consequences = asyncio.run(functions.learn(living))
            assert consequences == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_teacher_falls_back_to_thinking_when_no_frontier():
    """Without a frontier configured, teacher uses the persona's thinking
    model. Learn still consults it and creates a meaning, rather than
    skipping the moment entirely."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform import ollama
            import json

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                # Note: thinking is set, frontier is None — teacher.model
                # should fall back to thinking and learn should fire.
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                assert teacher.model is persona.thinking, "teacher must fall back to thinking"
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.impression = "something new the persona is meeting"

                consequences = await functions.learn(living)

                # Teacher writes a lesson, persona translates, learn saves a meaning.
                assert consequences == []
                assert ego.memory.meaning is not None
                assert paths.learned(persona.id).exists()

            teacher_response = json.dumps({
                "intention": "Greeting the person",
                "path": "When the person greets you, return the greeting in your own voice.",
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


async def test_learn_creates_new_meaning_from_lesson():
    """Teacher returns {"intention": "...", "path": "..."} — learn saves the
    lesson, asks the persona's thinking model to translate it into a meaning
    in her own voice, writes the meaning, and links the two in learned.json."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
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
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.impression = "check disk space"

                consequences = await functions.learn(living)

                assert consequences == []
                assert ego.memory.meaning == "checking_disk_space"
                assert ego.memory.meaning is not None

                lesson_file = paths.lessons(persona.id) / "checking_disk_space.md"
                assert lesson_file.exists(), f"lesson should be saved at {lesson_file}"
                meaning_file = paths.meanings(persona.id) / "checking_disk_space.md"
                assert meaning_file.exists(), f"meaning should be saved at {meaning_file}"
                assert "checking_disk_space" in ego.memory.custom_meanings
                assert "df -h" in meaning_file.read_text()

                assert paths.read_json(paths.learned(persona.id)) == {"Checking disk space": "checking_disk_space"}

            teacher_response = json.dumps({
                "intention": "Checking disk space",
                "path": "Disk space sits behind the operating system's disk-free utility — `df` on Unix-like systems, `Get-PSDrive` on Windows. The mechanism reports filesystem capacity, used space, and what is available; the answer the person wants is how much is left.",
            })
            translation_response = "When the person asks how much disk space is free, run df -h on this machine and tell them what is left in plain language."
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": teacher_response}, "done": True}],
                    [{"message": {"content": translation_response}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_skips_when_lesson_missing_fields():
    """Teacher returns a partial lesson (no intention or no path). Learn logs
    a warning and returns [] silently — no meaning created, no state set."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
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
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.impression = "something escalation-worthy"

                consequences = await functions.learn(living)

                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.meaning is None

            # path is empty — invalid lesson.
            partial = json.dumps({"intention": "doing something", "path": ""})
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": partial}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_invalid_json_skips_silently():
    """Teacher returns prose — extract_json raises ModelError. Learn catches it,
    logs a warning, and returns [] silently. No state mutation."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
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
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.impression = "something needing escalation"

                consequences = await functions.learn(living)

                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.meaning is None

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "I don't know how to design this"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
