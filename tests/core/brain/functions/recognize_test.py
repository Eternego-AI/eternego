from application.platform.processes import on_separate_process_async


async def test_escalation_prompt_includes_builtin_and_platform_tools():
    """When recognize escalates, the prompt must list every available tool —
    both built-in (say, save_destiny, etc.) and platform tools registered
    via @tool (e.g. OS.execute_on_sub_process)."""
    def isolated():
        import asyncio
        from application.core.brain import functions
        from application.core.brain.mind.memory import Memory
        from application.core.data import Message, Model, Persona, Prompt
        from application.platform import ollama

        captured = {}

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
            # Two calls: first is matching (returns 0 → escalate), second is escalation
            assert len(received) == 2, f"Expected 2 calls, got {len(received)}"
            escalation_prompt = received[1]["body"]["messages"][0]["content"]
            # Built-in tools must appear
            assert "say(text)" in escalation_prompt, "say tool missing"
            assert "save_destiny" in escalation_prompt, "save_destiny missing"
            assert "save_notes" in escalation_prompt, "save_notes missing"
            assert "recall_history" in escalation_prompt, "recall_history missing"
            assert "check_calendar" in escalation_prompt, "check_calendar missing"
            # Platform tools section must exist
            assert "Platform tools" in escalation_prompt, "Platform tools section missing"
            # OS shell tool must be discoverable from the registry
            assert "OS.execute_on_sub_process" in escalation_prompt or "execute_on_sub_process" in escalation_prompt, \
                "OS shell tool missing from platform tools"

        ollama.assert_call(
            run=lambda url: consume(url),
            validate=validate,
            responses=[
                # First call: recognize matching — return 0 (none of the above)
                [{"message": {"content": '{"ability": 0}'}, "done": True}],
                # Second call: escalation — return a valid generated meaning
                [{"message": {"content": '{"name": "checking", "code": "def intention(persona): return \\"...\\"\\ndef prompt(persona): return \\"...\\""}'}, "done": True}],
            ],
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
