"""Recognize stage — integration tests over a real Living.

Each test constructs a real Living (Ego/Eye/Consultant/Teacher + Pulse with a
no-op worker), calls `recognize(living)`, and asserts on:
- the returned consequences list
- memory state (cognitive signals via perception / comprehension)
- bus traffic (Tick/Tock signals, Command dispatches)

Recognize emits `{"decision": [<actions>]}` — a JSON object with one key
whose value is a list of actions to execute in order. Each action is one
of `{"say": ...}`, `{"done": null}`, `{"tools.<name>": {...}}`, or
`{"tools.load_instruction": {"intention": "..."}}`. Empty list = rest.
No prose fallback — non-JSON from the model raises `ModelError` and the
beat is skipped. Recognize gates on `memory.perception()` and
`memory.comprehension()`: if there's a pending intention or a fresh
impression, recognize skips so learn or decide runs.
"""

from application.platform.processes import on_separate_process_async


async def test_recognize_say_dispatches_command():
    """Top-level `{"say": "hello"}` dispatches a 'Persona wants to say' Command
    and returns []."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import observer, ollama

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
                ego.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.recognize(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == [], f"expected [], got {consequences!r}"
                assert said == ["hello"], f"expected one say 'hello', got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"decision": [{"say": "hello"}]}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_done_returns_empty():
    """`{"done": null}` returns [] with no Command and no memory writes."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import observer, ollama

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
                ego.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                msgs_before = len(ego.memory.messages)
                consequences = await functions.recognize(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert said == [], f"done should not dispatch a say, got {said!r}"
                assert len(ego.memory.messages) == msgs_before

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"decision": [{"done": null}]}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_load_instruction_records_intention():
    """`{"tools.load_instruction": {"intention": "..."}}` records the
    persona's intention via memory.intention() but does NOT execute (no
    consequence). Learn will fire next on the same beat and produce the
    matching impression."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
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
                ego.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))

                consequences = await functions.recognize(living)

                assert consequences == [], "load_instruction is cognitive — no consequence"
                # Perception should report the pending intention.
                assert ego.memory.perception() == "chatting"

            payload = '{"decision": [{"tools.load_instruction": {"intention": "chatting"}}]}'
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": payload}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_tool_returns_capability():
    """`{"tools.<name>": {...}}` returns a single-item capability list for
    clock's executor to run."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
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
                ego.memory.remember(Message(content="ls", prompt=Prompt(role="user", content="ls")))

                consequences = await functions.recognize(living)

                assert len(consequences) == 1
                assert consequences[0] == {"tools.OS.execute": {"command": "ls"}}

            payload = '{"decision": [{"tools.OS.execute": {"command": "ls"}}]}'
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": payload}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_steps_returns_list():
    """`{"decision": [...]}` with multiple items returns the consequences in order. Voice runs
    inline (dispatched as Command); tools queue for clock."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import observer, ollama

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
                ego.memory.remember(Message(content="ls", prompt=Prompt(role="user", content="ls")))

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.recognize(living)
                import asyncio as _a
                await _a.sleep(0)

                assert len(consequences) == 2
                assert consequences[0] == {"tools.OS.execute": {"command": "ls"}}
                assert consequences[1] == {"tools.OS.execute": {"command": "pwd"}}
                assert said == ["checking"]

            payload = (
                '{"decision": ['
                '{"say": "checking"},'
                '{"tools.OS.execute": {"command": "ls"}},'
                '{"tools.OS.execute": {"command": "pwd"}}'
                ']}'
            )
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": payload}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_skips_when_intention_pending():
    """If perception() returns a pending intention, recognize skips —
    learn should run next, not recognize."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
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
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            ego.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))
            ego.memory.intention("chatting")

            # No model call should be made — recognize gates and returns [].
            consequences = asyncio.run(functions.recognize(living))
            assert consequences == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_skips_when_impression_present():
    """If comprehension() returns a fresh impression (decide's cue),
    recognize skips so decide runs."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
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
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            ego.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))
            ego.memory.intention("chatting")
            ego.memory.impression("talk simply")

            consequences = asyncio.run(functions.recognize(living))
            assert consequences == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error



async def test_recognize_empty_stream_propagates_engine_error():
    """Empty model stream (OOM, load failure) raises EngineConnectionError —
    it's an infrastructure fault, not a cognitive one. Tick catches and exits."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.core.exceptions import EngineConnectionError
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
                ego.memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))

                try:
                    await functions.recognize(living)
                    assert False, "expected EngineConnectionError"
                except EngineConnectionError:
                    pass

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[]],  # empty stream
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


