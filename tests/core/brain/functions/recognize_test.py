"""Recognize stage — integration tests over a real Living.

Each test constructs a real Living (Ego/Eye/Consultant/Teacher + Pulse with a
no-op worker), calls `recognize(living)`, and asserts on:
- the returned consequences list
- memory state (impression / meaning / ability / messages)
- bus traffic (Tick/Tock signals, Command dispatches)
"""

from application.platform.processes import on_separate_process_async


def _build_living(persona):
    """Helper duplicated in each isolated() body — kept inline by tradition,
    but extracted here so the spec of "what setup looks like" is one place."""
    raise NotImplementedError("Inline this in each test for separate-process isolation")


async def test_recognize_dispatches_say_and_clears_state():
    """When the model emits {"say": "..."}, recognize dispatches a Persona-wants-to-say
    Command and clears memory.meaning/ability/impression. Returns [] (no capabilities)."""
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
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0
                assert ego.memory.impression == ""
                assert said == ["hello"], f"expected one say 'hello', got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"say": "hello"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_done_clears_state():
    """{"done": null} clears meaning/ability/impression. No consequences, no say."""
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
                ego.memory.meaning = "stale"
                ego.memory.ability = 5
                ego.memory.impression = "stale"

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.recognize(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0
                assert ego.memory.impression == ""
                assert said == [], f"done should not dispatch a say, got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"done": null}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_meaning_selected_sets_state():
    """{"meanings.chatting": "<impression>"} sets memory.meaning + ability and
    leaves the impression for decide. Returns [] (decide takes over next stage)."""
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

                assert consequences == []
                assert ego.memory.meaning == "chatting"
                assert ego.memory.ability != 0, "chatting is a built-in meaning, ability should be set"
                assert ego.memory.impression == "casual greeting"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"meanings.chatting": "casual greeting"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_tool_returns_capability():
    """{"tools.OS.execute_on_sub_process": {...}} returns a single-item capability
    list for clock's executor to run. Memory state cleared (ability=0, meaning=None)."""
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
                assert consequences[0] == {"tools.OS.execute_on_sub_process": {"command": "ls"}}
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"tools.OS.execute_on_sub_process": {"command": "ls"}}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_prose_forces_troubleshooting():
    """When the model returns prose with no JSON, recognize dispatches the prose as
    a say and forces memory.meaning='troubleshooting' so decide can self-diagnose
    on the next stage. Returns []."""
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

                assert consequences == []
                assert ego.memory.meaning == "troubleshooting"
                assert ego.memory.ability != 0
                assert any("just some prose" in t for t in said), \
                    f"expected the prose dispatched as a say, got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "just some prose, no json here"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_prose_during_troubleshooting_raises():
    """Second prose response while already on troubleshooting raises BrainException
    (attributed to thinking model). Health_check sees the BrainFault next tick."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.core.exceptions import BrainException
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
                ego.memory.meaning = "troubleshooting"
                ego.memory.ability = 8

                try:
                    await functions.recognize(living)
                    assert False, "expected BrainException"
                except BrainException as e:
                    assert e.model is persona.thinking

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "still prose"}, "done": True}]],
            )

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


async def test_recognize_prose_alongside_json_dispatches_both():
    """When the model returns prose AND a JSON action, the prose is dispatched as a
    say and the action runs as its own step (intelligence is words after words —
    if the model wrote prose alongside the action, those words go to the person)."""
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

                assert consequences == []
                assert ego.memory.meaning is None
                # The prose lands as a say. Done is the action.
                assert any("I'm sitting with this" in t for t in said), \
                    f"expected the prose dispatched, got {said!r}"

            raw = (
                "I'm sitting with this. Nothing calls right now.\n\n"
                "```json\n"
                '{"done": null}\n'
                "```"
            )
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": raw}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
