from application.platform.processes import on_separate_process_async


async def test_wondering_passes_when_ability_is_set():
    """If recognize already picked an ability, wondering returns True without any model call."""
    def isolated():
        import asyncio
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
            from application.core.data import Model, Persona

            persona = Persona(
                id="test-persona",
                name="Tester",
                thinking=Model(name="llama3", url="not required"),
                base_model="llama3",
            )
            memory = Memory(persona)
            memory.ability = 3
            memory.meaning = "chatting"
            ego = agents.Ego(persona, FakeWorker())
            result = asyncio.run(functions.wondering(ego, "teacher", memory))
            assert result is True
            assert memory.meaning == "chatting"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_wondering_prompt_includes_builtin_and_platform_tools():
    """When wondering consults the teacher, the prompt lists every available tool —
    built-ins and platform tools registered via @tool — and accepts the full
    meaning module in one response."""
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
                memory.ability = 0
                memory.impression = "check disk space"
                ego = agents.Ego(persona, FakeWorker())
                await functions.wondering(ego, "teacher", memory)

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 1, f"Expected 1 teacher call, got {len(items)}"
                messages = items[0]["body"]["messages"]
                text = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
                assert "say(text)" in text, "say tool missing"
                assert "save_destiny" in text, "save_destiny missing"
                assert "save_notes" in text, "save_notes missing"
                assert "recall_history" in text, "recall_history missing"
                assert "check_calendar" in text, "check_calendar missing"
                assert "Platform tools" in text, "Platform tools section missing"
                assert "OS.execute_on_sub_process" in text or "execute_on_sub_process" in text, \
                    "OS shell tool missing from platform tools"

            import json as _json
            teacher_json = _json.dumps({
                "reason": "no existing meaning checks system state",
                "new_meaning": "checking_disk_space",
                "code_lines": valid_module.splitlines(),
            })

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[[{"message": {"content": teacher_json}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
