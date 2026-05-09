"""Recognize stage — integration tests over a real Living.

Each test constructs a real Living (Ego/Eye/Consultant/Teacher + Pulse with a
no-op worker), calls `recognize(living)`, and asserts on:
- the returned consequences list
- memory state (impression / meaning / messages)
- bus traffic (Tick/Tock signals, Command dispatches)

Recognize emits a tagged JSON object with an `action` discriminator
(`act`, `decide`, `done`) plus optional voice fields (`say`). Free-form
prose around the JSON is dispatched as a fallback say.
"""

from application.platform.processes import on_separate_process_async


async def test_recognize_say_field_dispatches_and_clears_state():
    """Top-level `say` field dispatches a Persona-wants-to-say Command and
    clears memory.meaning/impression. Returns [] (no capabilities)."""
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
                assert ego.memory.impression == ""
                assert said == ["hello"], f"expected one say 'hello', got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"action": "say", "say": "hello"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_done_clears_state():
    """{"action": "done"} clears meaning/impression. No consequences, no say."""
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
                assert ego.memory.impression == ""
                assert said == [], f"done should not dispatch a say, got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"action": "done"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_decide_meaning_sets_state():
    """{"action": "decide", "meaning": "chatting", "impression": "..."} sets
    memory.meaning and leaves the impression for decide. Returns []
    (decide takes over next stage)."""
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
                assert ego.memory.meaning == "chatting"
                assert ego.memory.impression == "casual greeting"

            payload = '{"action": "decide", "meaning": "chatting", "impression": "casual greeting"}'
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": payload}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_act_returns_capabilities():
    """{"action": "act", "capabilities": [...]} returns the capabilities list
    for clock's executor to run. Memory state cleared (meaning=None)."""
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
                assert ego.memory.meaning is None

            payload = '{"action": "act", "capabilities": [{"tools.OS.execute": {"command": "ls"}}]}'
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": payload}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_action_say_with_text_field_dispatches():
    """Some models pick `action: "say"` and put the text in `text` or `voice`
    rather than the documented `say` field. Recognize tolerates this and
    dispatches the text from whichever field carries it."""
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
                assert any("hello there" in t for t in said), \
                    f"text in voice/text field should dispatch as say, got {said!r}"

            payload = '{"action": "say", "text": "hello there"}'
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": payload}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_prose_dispatched_as_say():
    """When the model returns prose with no JSON, recognize dispatches the prose
    as a say (fallback for models that don't follow the schema). Returns []
    with state cleared."""
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
                assert any("just some prose" in t for t in said), \
                    f"expected the prose dispatched as a say, got {said!r}"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "just some prose, no json here"}, "done": True}]],
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
                '{"action": "done"}\n'
                "```"
            )
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": raw}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
