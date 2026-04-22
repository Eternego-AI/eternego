from application.platform.processes import on_separate_process_async


async def test_empty_stream_does_not_escalate():
    """When the local model returns an empty stream (ollama OOM / load fail), recognize must
    raise EngineConnectionError — no fallback impression, no frontier call."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.mind.memory import Memory

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass
            from application.core.data import Message, Model, Persona, Prompt
            from application.core.exceptions import EngineConnectionError
            from application.platform import ollama

            async def consume(url):
                persona = Persona(
                    id="test-persona",
                    name="Tester",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                    frontier=Model(name="frontier", provider="anthropic", api_key="x", url=url),
                )
                memory = Memory(persona)
                memory.remember(Message(
                    content="Hello",
                    prompt=Prompt(role="user", content="Hello"),
                ))
                try:
                    ego = agents.Ego(persona, FakeWorker())
                    await functions.recognize(ego, "identity here", memory)
                    assert False, "Expected EngineConnectionError"
                except EngineConnectionError:
                    pass

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 1, f"Expected exactly 1 call (no escalation), got {len(items)}"

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[[]],  # empty stream — simulates OOM
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_prose_forces_troubleshooting_and_returns_true():
    """When the model returns prose instead of JSON, recognize dispatches the
    prose as a say and forces memory.meaning = 'troubleshooting' so decide
    can run the self-diagnostic ability next — returns True to continue tick."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.mind.memory import Memory

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            async def consume(url):
                persona = Persona(
                    id="test-persona",
                    name="Tester",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                memory = Memory(persona)
                memory.remember(Message(
                    content="Hello",
                    prompt=Prompt(role="user", content="Hello"),
                ))
                ego = agents.Ego(persona, FakeWorker())
                result = await functions.recognize(ego, "identity here", memory)
                assert result is True, "Expected True — recognize forces troubleshooting and hands off to decide"
                assert memory.meaning == "troubleshooting", f"Expected meaning=troubleshooting, got {memory.meaning!r}"
                assert memory.ability != 0, f"Expected ability set after forcing, got {memory.ability}"
                # Prose was dispatched as say — assistant-role message should have it
                assistant_contents = [
                    m.prompt.content for m in memory.messages
                    if m.prompt and m.prompt.role == "assistant"
                ]
                assert any("just some text no json" in c for c in assistant_contents), \
                    f"Expected the prose as assistant content, got {assistant_contents!r}"

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 1, f"Expected exactly 1 call, got {len(items)}"

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[[{"message": {"content": "just some text no json"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_prose_while_on_troubleshooting_raises_brain_exception():
    """When recognize refuses prose while memory.meaning is already 'troubleshooting'
    (meaning the forced recovery already happened once), it raises BrainException
    attributed to the thinking model — tick catches and health_check marks sick on
    next heartbeat."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.mind.memory import Memory

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass
            from application.core.data import Message, Model, Persona, Prompt
            from application.core.exceptions import BrainException
            from application.platform import ollama

            async def consume(url):
                persona = Persona(
                    id="test-persona",
                    name="Tester",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                memory = Memory(persona)
                memory.remember(Message(content="Hi", prompt=Prompt(role="user", content="Hi")))
                # Simulate the state AFTER a prior forced-troubleshooting cycle
                memory.meaning = "troubleshooting"
                memory.ability = 8
                ego = agents.Ego(persona, FakeWorker())
                try:
                    await functions.recognize(ego, "identity here", memory)
                    assert False, "Expected BrainException"
                except BrainException as err:
                    assert err.model is persona.thinking, "exception should attribute to thinking model"

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 1

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[[{"message": {"content": "still no json"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_no_impression_stays_at_ability_zero():
    """If the model returns valid JSON with ability=0 and empty impression, recognize
    leaves memory.ability=0 and memory.meaning=None — wondering is the stage that
    handles ability==0, and it will see an empty impression and skip there. Only one
    model call from recognize itself."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.mind.memory import Memory

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            async def consume(url):
                persona = Persona(
                    id="test-persona",
                    name="Tester",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                memory = Memory(persona)
                memory.remember(Message(
                    content="Hi",
                    prompt=Prompt(role="user", content="Hi"),
                ))
                ego = agents.Ego(persona, FakeWorker())
                result = await functions.recognize(ego, "identity here", memory)
                assert result is True, "recognize returns True once the model cooperated"
                assert memory.ability == 0, f"Expected ability=0, got {memory.ability}"
                assert memory.meaning is None, f"Expected meaning=None, got {memory.meaning!r}"
                assert memory.impression == "", f"Expected impression='', got {memory.impression!r}"

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 1, f"Expected exactly 1 call (no escalation), got {len(items)}"

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[[{"message": {"content": '{"impression": "", "ability": 0}'}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
