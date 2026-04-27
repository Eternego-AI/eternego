"""Learn stage — integration tests over a real Living.

Each test constructs a Living (Ego/Eye/Consultant/Teacher + Pulse with no-op
worker), seeds memory state to the precondition learn expects, calls
`learn(living)`, and asserts on returned consequences and memory state.
"""

from application.platform.processes import on_separate_process_async


async def test_learn_passes_when_ability_already_set():
    """If recognize already chose a meaning (memory.ability != 0), learn passes
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
            ego.memory.ability = 3
            ego.memory.meaning = "chatting"
            ego.memory.impression = "doesn't matter"

            consequences = asyncio.run(functions.learn(living))
            assert consequences == []
            assert ego.memory.meaning == "chatting"
            assert ego.memory.ability == 3

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
            ego.memory.ability = 0
            ego.memory.impression = ""

            consequences = asyncio.run(functions.learn(living))
            assert consequences == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_passes_when_no_frontier():
    """Without a frontier model, learn cannot consult a teacher. Passes through
    silently — no consequences, no message injected."""
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
            ego.memory.ability = 0
            ego.memory.impression = "something the persona doesn't know how to handle"
            messages_before = len(ego.memory.messages)

            consequences = asyncio.run(functions.learn(living))
            assert consequences == []
            assert len(ego.memory.messages) == messages_before

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_existing_meaning_sets_state():
    """Teacher returns {"meanings.chatting": "<impression>"} — recognize simply
    missed it. Learn sets memory.meaning + ability so decide takes over next."""
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
                ego.memory.ability = 0
                ego.memory.impression = "casual greeting"

                consequences = await functions.learn(living)

                assert consequences == []
                assert ego.memory.meaning == "chatting"
                assert ego.memory.ability != 0
                assert ego.memory.impression == "casual greeting"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"meanings.chatting": "casual greeting"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_creates_new_meaning():
    """Teacher returns {"new_meaning": {"name": "...", "code_lines": [...]}} —
    learn writes the module to disk, loads it, and sets memory.meaning + ability
    so decide takes over next."""
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

            valid_module_lines = [
                '"""Meaning — checking_disk_space."""',
                'from application.core.data import Persona',
                'class Meaning:',
                '    def __init__(self, persona: Persona):',
                '        self.persona = persona',
                '    def intention(self) -> str:',
                '        return "Checking disk space"',
                '    def path(self) -> str:',
                '        return "stub path text"',
            ]

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
                ego.memory.ability = 0
                ego.memory.impression = "check disk space"

                consequences = await functions.learn(living)

                assert consequences == []
                assert ego.memory.meaning == "checking_disk_space"
                assert ego.memory.ability != 0
                module_file = paths.meanings(persona.id) / "checking_disk_space.py"
                assert module_file.exists(), f"meaning module should be saved at {module_file}"
                assert "checking_disk_space" in ego.memory.custom_meanings

            teacher_response = json.dumps({
                "new_meaning": {
                    "name": "checking_disk_space",
                    "code_lines": valid_module_lines,
                }
            })
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": teacher_response}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_learn_returns_capability_for_tool():
    """Teacher returns {"tools.<name>": {...args}} — learn declares it as a
    consequence; clock's executor will run it. No state set, no message added."""
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
                ego.memory.ability = 0
                ego.memory.impression = "list files"

                consequences = await functions.learn(living)

                assert len(consequences) == 1
                assert consequences[0] == {"tools.OS.execute_on_sub_process": {"command": "ls"}}
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"tools.OS.execute_on_sub_process": {"command": "ls"}}'}, "done": True}]],
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
                ego.memory.ability = 0
                ego.memory.impression = "something needing escalation"

                consequences = await functions.learn(living)

                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "I don't know how to design this"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
