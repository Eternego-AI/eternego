from application.platform.processes import on_separate_process_async


async def test_escalation_prompt_includes_builtin_and_platform_tools():
    """When recognize escalates, the single escalation call must list every available tool —
    both built-in (say, save_destiny, etc.) and platform tools registered via @tool
    (e.g. OS.execute_on_sub_process) — and accept the full meaning module in one response."""
    def isolated():
        from application.core.brain import functions
        from application.core.brain.mind.memory import Memory
        from application.core.data import Message, Model, Persona, Prompt
        from application.platform import ollama

        valid_module = (
            '"""Meaning — checking."""\n'
            'from application.core.data import Persona\n'
            'def intention(persona: Persona) -> str:\n'
            '    return "The person wants Tester to check disk space."\n'
            'def prompt(persona: Persona) -> str:\n'
            '    return "stub"\n'
        )

        async def consume(url):
            persona = Persona(
                id="test-persona",
                name="Tester",
                thinking=Model(name="llama3", url=url),
                base_model="llama3",
            )
            memory = Memory(persona)
            memory.add(Message(
                content="Can you check my disk space?",
                prompt=Prompt(role="user", content="Can you check my disk space?"),
            ))
            await functions.recognize(persona, "identity here", memory)

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
