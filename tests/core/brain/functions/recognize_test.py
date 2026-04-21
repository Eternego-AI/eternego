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


async def test_invalid_json_retries_without_escalation():
    """When the local model returns garbage (not JSON), recognize must add an [invalid_json] seed
    message and return False — but must NOT escalate to frontier (would burn money)."""
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
                    frontier=Model(name="frontier", provider="anthropic", api_key="x", url=url),
                )
                memory = Memory(persona)
                memory.remember(Message(
                    content="Hello",
                    prompt=Prompt(role="user", content="Hello"),
                ))
                ego = agents.Ego(persona, FakeWorker())
                result = await functions.recognize(ego, "identity here", memory)
                assert result is False, "Expected False on ModelError"
                # Memory should now contain [invalid_json] seed for the next retry
                assert any(
                    "[invalid_json]" in (m.content or "")
                    for m in memory.messages
                ), "Expected [invalid_json] seed in memory"

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 1, f"Expected exactly 1 call (no escalation), got {len(items)}"

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[[{"message": {"content": "just some text no json"}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_no_impression_does_not_escalate():
    """If the model returns valid JSON with ability=0 but an empty impression, recognize must NOT
    escalate (cheap failure path)."""
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
                    frontier=Model(name="frontier", provider="anthropic", api_key="x", url=url),
                )
                memory = Memory(persona)
                memory.remember(Message(
                    content="Hi",
                    prompt=Prompt(role="user", content="Hi"),
                ))
                ego = agents.Ego(persona, FakeWorker())
                result = await functions.recognize(ego, "identity here", memory)
                assert result is False, "Expected False when no impression"

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


async def test_escalation_prompt_includes_builtin_and_platform_tools():
    """When recognize escalates, the single escalation call must list every available tool —
    both built-in (say, save_destiny, etc.) and platform tools registered via @tool
    (e.g. OS.execute_on_sub_process) — and accept the full meaning module in one response."""
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

            valid_module = (
                '"""Meaning — checking_disk_space."""\n'
                'from application.core.data import Persona\n'
                'class Meaning:\n'
                '    def __init__(self, persona: Persona):\n'
                '        self.persona = persona\n'
                '    def intention(self) -> str:\n'
                '        return "Checking disk space"\n'
                '    def prompt(self) -> str:\n'
                '        return "stub"\n'
            )

            async def consume(url):
                persona = Persona(
                    id="test-persona",
                    name="Tester",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                memory = Memory(persona)
                memory.remember(Message(
                    content="Can you check my disk space?",
                    prompt=Prompt(role="user", content="Can you check my disk space?"),
                ))
                ego = agents.Ego(persona, FakeWorker())
                await functions.recognize(ego, "identity here", memory)

            def validate(received):
                # Two calls: matching (→ 0) and escalation (producing name + code)
                assert len(received) == 2, f"Expected 2 calls, got {len(received)}"
                escalation_messages = received[1]["body"]["messages"]
                escalation_text = " ".join(m["content"] for m in escalation_messages if isinstance(m.get("content"), str))
                # Built-in tools must appear in the escalation
                assert "say(text)" in escalation_text, "say tool missing"
                assert "save_destiny" in escalation_text, "save_destiny missing"
                assert "save_notes" in escalation_text, "save_notes missing"
                assert "recall_history" in escalation_text, "recall_history missing"
                assert "check_calendar" in escalation_text, "check_calendar missing"
                # Platform tools section must exist
                assert "Platform tools" in escalation_text, "Platform tools section missing"
                # OS shell tool must be discoverable from the registry
                assert "OS.execute_on_sub_process" in escalation_text or "execute_on_sub_process" in escalation_text, \
                    "OS shell tool missing from platform tools"

            import json as _json
            escalation_json = _json.dumps({
                "reason": "no existing meaning checks system state",
                "new_meaning": "checking_disk_space",
                "code_lines": valid_module.splitlines(),
            })

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[
                    # First call: recognize matching — return 0 (none of the above)
                    [{"message": {"content": '{"impression": "no ability", "ability": 0}'}, "done": True}],
                    # Second call: escalation — name + code in one response
                    [{"message": {"content": escalation_json}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
