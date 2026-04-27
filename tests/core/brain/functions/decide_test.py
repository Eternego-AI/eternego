"""Decide stage — integration tests over a real Living.

Each test seeds memory with a meaning name (recognize already chose), constructs
a real Living, calls `decide(living)`, and asserts on consequences, dispatched
Commands, and memory state. State always clears at the end of decide regardless
of which branch ran.
"""

from application.platform.processes import on_separate_process_async


async def test_decide_no_meaning_passes_through():
    """If memory.meaning is None or unknown, decide returns [] without a model
    call (no meaning, nothing to act on)."""
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

            consequences = asyncio.run(functions.decide(living))
            assert consequences == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_say_dispatches_and_clears_state():
    """{"say": "..."} dispatches a 'Persona wants to say' Command and clears
    memory.meaning/ability."""
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
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.decide(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0
                assert said == ["hi there"]

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"say": "hi there"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_done_clears_state():
    """{"done": null} clears state. No consequences, no dispatched commands."""
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
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                consequences = await functions.decide(living)
                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"done": null}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_notify_remembers_and_dispatches():
    """{"notify": "<text>"} adds an assistant message to memory and dispatches
    a 'Persona wants to notify' Command."""
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
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                notified = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to notify":
                        notified.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                msgs_before = len(ego.memory.messages)
                consequences = await functions.decide(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert notified == ["broadcast this"]
                assert len(ego.memory.messages) == msgs_before + 1
                last = ego.memory.messages[-1]
                assert last.prompt.role == "assistant"
                assert last.content == "broadcast this"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"notify": "broadcast this"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_clear_memory_forgets_and_records():
    """{"clear_memory": null} wipes messages and records a tool-result pair so
    the persona's next read sees that it just cleared its own memory."""
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
                ego.memory.remember(Message(content="old chatter", prompt=Prompt(role="user", content="old chatter")))
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                consequences = await functions.decide(living)
                assert consequences == []
                # Memory is forgotten then add_tool_result pair appended → 2 messages.
                assert len(ego.memory.messages) == 2
                call_msg, result_msg = ego.memory.messages
                assert call_msg.prompt.role == "assistant"
                assert "clear_memory" in call_msg.content
                assert "TOOL_RESULT" in result_msg.content
                assert "memory cleared" in result_msg.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"clear_memory": null}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_remove_meaning_unlearns_existing():
    """{"remove_meaning": {"name": "<existing>"}} deletes the file, calls
    memory.unlearn, and records a success TOOL_RESULT."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions, meanings
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            valid_module = (
                '"""Meaning — temp_meaning."""\n'
                'from application.core.data import Persona\n'
                'class Meaning:\n'
                '    def __init__(self, persona: Persona):\n'
                '        self.persona = persona\n'
                '    def intention(self) -> str:\n'
                '        return "Temp"\n'
                '    def path(self) -> str:\n'
                '        return "stub"\n'
            )

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                meanings.save_meaning(persona.id, "temp_meaning", valid_module)
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                instance = meanings.load(persona, "temp_meaning")
                ego.memory.learn("temp_meaning", instance)
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                consequences = await functions.decide(living)
                assert consequences == []
                meaning_file = paths.meanings(persona.id) / "temp_meaning.py"
                assert not meaning_file.exists(), "module file should be deleted"
                assert "temp_meaning" not in ego.memory.custom_meanings
                last = ego.memory.messages[-1]
                assert "TOOL_RESULT" in last.content
                assert "removed meaning: temp_meaning" in last.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"remove_meaning": {"name": "temp_meaning"}}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_stop_dispatches_command():
    """{"stop": null} dispatches a 'Persona requested stop' Command."""
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
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                stops = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona requested stop":
                        stops.append(cmd)
                observer.subscribe(capture)

                consequences = await functions.decide(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert len(stops) == 1

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"stop": null}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_tool_returns_capability():
    """{"tools.<name>": {...}} returns a single-item capability list for
    clock's executor to run. State cleared."""
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
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                consequences = await functions.decide(living)
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


async def test_decide_prose_dispatches_as_say_and_clears_state():
    """When the model returns prose with no JSON, decide dispatches the prose as
    a say. State always clears at end of decide. Returns []."""
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
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                ego.memory.meaning = "chatting"
                ego.memory.ability = 1

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.decide(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert ego.memory.meaning is None
                assert ego.memory.ability == 0
                assert any("just thinking aloud" in t for t in said)

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": "just thinking aloud, no action"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


