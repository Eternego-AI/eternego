"""Decide stage — integration tests over a real Living.

Each test seeds memory with an intention + matching impression (the
state decide requires), constructs a real Living, calls `decide(living)`,
and asserts on consequences, dispatched Commands, and memory state.

Decide gates on `memory.comprehension()` — it only fires after learn has
produced an impression. The body lives in the conversation; decide reads
it via memory.prompts and acts on it.

Decide's vocabulary is the single-key / `steps:[...]` shape recognize uses,
plus self-care specials (clear_memory, remove_meaning, stop) handled inline.
"""

from application.platform.processes import on_separate_process_async


async def test_decide_no_impression_passes_through():
    """If `memory.comprehension()` is None, decide returns [] without a
    model call (gate didn't fire)."""
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


async def test_decide_say_dispatches_command():
    """`{"say": "..."}` dispatches a 'Persona wants to say' Command."""
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
                ego.memory.intention("chatting")
                ego.memory.impression("talk simply")

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.decide(living)
                import asyncio as _a
                await _a.sleep(0)

                assert consequences == []
                assert said == ["hi there"]

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"say": "hi there"}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_done_returns_empty():
    """`{"done": null}` returns [] with no Command."""
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
                ego.memory.intention("chatting")
                ego.memory.impression("rest is fine")

                consequences = await functions.decide(living)
                assert consequences == []

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"done": null}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_notify_remembers_and_dispatches():
    """`{"notify": "<text>"}` adds an assistant message to memory and dispatches
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
                ego.memory.intention("broadcasting")
                ego.memory.impression("broadcast on every channel")

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
    """`{"clear_memory": null}` wipes messages then records a tool-result pair so
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
                ego.memory.intention("resetting")
                ego.memory.impression("wipe and start fresh")

                consequences = await functions.decide(living)
                assert consequences == []
                # forget() then add_tool_result writes 2 messages → 2 messages total.
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
    """`{"remove_meaning": {"name": "<existing>"}}` deletes the file, calls
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

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                paths.save_as_string(paths.meanings(persona.id) / "temp_meaning.md", "# Temp\n\nstub\n")
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.learn("temp_meaning", meanings.Meaning("temp_meaning", "Temp", "stub"))
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                ego.memory.intention("pruning")
                ego.memory.impression("drop the stale meaning")

                consequences = await functions.decide(living)
                assert consequences == []
                meaning_file = paths.meanings(persona.id) / "temp_meaning.md"
                assert not meaning_file.exists(), "meaning file should be deleted"
                assert "temp_meaning" not in ego.memory.custom_meanings
                last = ego.memory.messages[-1]
                assert "TOOL_RESULT" in last.content
                assert "removed instruction: temp_meaning" in last.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"remove_meaning": {"name": "temp_meaning"}}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_stop_dispatches_command():
    """`{"stop": null}` dispatches a 'Persona requested stop' Command."""
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
                ego.memory.intention("stopping")
                ego.memory.impression("stop here")

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
                ego.memory.intention("listing")
                ego.memory.impression("run ls -la")

                consequences = await functions.decide(living)
                assert len(consequences) == 1
                assert consequences[0] == {"tools.OS.execute": {"command": "ls"}}

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"tools.OS.execute": {"command": "ls"}}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_steps_returns_list_of_capabilities():
    """`{"steps": [...]}` returns multiple consequences in order. Voice and
    specials run inline; tools queue for clock."""
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
                ego.memory.intention("exploring")
                ego.memory.impression("describe then list")

                said = []
                async def capture(cmd: observer.Command):
                    if cmd.title == "Persona wants to say":
                        said.append(cmd.details.get("text", ""))
                observer.subscribe(capture)

                consequences = await functions.decide(living)
                import asyncio as _a
                await _a.sleep(0)

                # Two queued capabilities, one inline say.
                assert len(consequences) == 2
                assert consequences[0] == {"tools.OS.execute": {"command": "ls"}}
                assert consequences[1] == {"tools.OS.execute": {"command": "pwd"}}
                assert said == ["checking"]

            payload = (
                '{"steps": ['
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



async def test_decide_remove_meaning_clears_learned_entry():
    """remove_meaning also drops the lesson_id mapping in learned.json so the
    map doesn't keep stale entries for deleted meanings."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions, meanings
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama
            from application.core import paths

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                paths.save_as_string(paths.meanings(persona.id) / "temp_meaning.md", "# Temp\n\nstub\n")
                paths.save_as_json(persona.id, paths.learned(persona.id), {"temp_meaning": "temp_meaning"})

                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.learn("temp_meaning", meanings.Meaning("temp_meaning", "Temp", "stub"))
                ego.memory.remember(Message(content="hi", prompt=Prompt(role="user", content="hi")))
                ego.memory.intention("pruning")
                ego.memory.impression("drop it")

                consequences = await functions.decide(living)
                assert consequences == []
                assert paths.read_json(paths.learned(persona.id)) == {}

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": '{"remove_meaning": {"name": "temp_meaning"}}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
