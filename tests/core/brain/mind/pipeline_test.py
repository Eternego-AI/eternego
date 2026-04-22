"""Integration tests for the full cognitive pipeline.

Walks a complete tick — realize → recognize → wondering → decide → experience
— with scripted model responses at each stage, and asserts the memory state
after each step and the end-to-end outcome.
"""

from application.platform.processes import on_separate_process_async


async def test_text_message_produces_say_via_chatting():
    """Person sends 'Hi'. Recognize picks chatting (ability 1). Wondering skips.
    Decide plans a say. Experience dispatches it. Memory ends with the persona's
    spoken reply as a role=assistant message."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.functions import decide, experience, realize, recognize, wondering
            from application.core.brain.mind.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass
                def reset(self): pass

            async def consume(url):
                persona = Persona(
                    id="pipeline-test",
                    name="Pipe",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                paths.home(persona.id).mkdir(parents=True, exist_ok=True)

                memory = Memory(persona)
                memory.remember(Message(
                    content="Hi",
                    prompt=Prompt(role="user", content="Hi"),
                ))

                ego = agents.Ego(persona, FakeWorker())

                # realize: text-only message, no model call, just sets prompt (already set)
                r_realize = await realize(ego, ego.perspective(), memory)
                assert r_realize is True

                # recognize: 1 model call -> ability=1 (chatting)
                r_recognize = await recognize(ego, ego.personality(), memory)
                assert r_recognize is True
                assert memory.ability == 1, f"Expected chatting (1), got {memory.ability}"
                assert memory.meaning == "chatting", f"Expected chatting, got {memory.meaning!r}"

                # wondering: passes through (ability != 0)
                r_wonder = await wondering(ego, ego.teacher(), memory)
                assert r_wonder is True

                # decide: 1 model call -> say plan
                r_decide = await decide(ego, ego.personality(), memory)
                assert r_decide is True
                assert memory.plan == {"tool": "say", "text": "Hello Pipe"}, f"Unexpected plan: {memory.plan!r}"

                # experience: dispatches say, writes assistant message, no model call
                r_experience = await experience(ego, ego.personality(), memory)
                assert r_experience is True

                # Final memory should end with assistant "Hello Pipe"
                last = memory.messages[-1]
                assert last.prompt is not None
                assert last.prompt.role == "assistant"
                assert last.prompt.content == "Hello Pipe"

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 2, f"Expected 2 calls (recognize, decide), got {len(items)}"
                # First call: recognize
                recognize_text = " ".join(m.get("content", "") for m in items[0]["body"]["messages"] if isinstance(m.get("content"), str))
                assert "Recognize what this moment calls for" in recognize_text, "recognize prompt not found"
                # Second call: decide
                decide_text = " ".join(m.get("content", "") for m in items[1]["body"]["messages"] if isinstance(m.get("content"), str))
                assert "Chatting" in decide_text or "chatting" in decide_text, "decide prompt not found"

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[
                    # recognize returns chatting
                    [{"message": {"content": '{"impression": "greeting", "ability": 1}'}, "done": True}],
                    # decide returns a say plan
                    [{"message": {"content": '{"tool": "say", "text": "Hello Pipe"}'}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_ability_zero_triggers_wondering():
    """When recognize returns ability=0, wondering kicks in and consults the
    teacher — one additional model call beyond recognize. Teacher names an
    existing meaning."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.functions import recognize, wondering
            from application.core.brain.mind.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="pipeline-wonder",
                    name="Pipe",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                paths.home(persona.id).mkdir(parents=True, exist_ok=True)

                memory = Memory(persona)
                memory.remember(Message(
                    content="unusual thing",
                    prompt=Prompt(role="user", content="unusual thing"),
                ))

                ego = agents.Ego(persona, FakeWorker())

                await recognize(ego, ego.personality(), memory)
                assert memory.ability == 0, f"Expected ability=0, got {memory.ability}"
                assert memory.impression == "cannot place this", f"Unexpected impression: {memory.impression!r}"

                r_wonder = await wondering(ego, ego.teacher(), memory)
                assert r_wonder is True
                assert memory.meaning == "chatting", f"Expected teacher to pick chatting, got {memory.meaning!r}"
                assert memory.ability != 0, f"Expected ability set after teacher, got {memory.ability}"

            def validate(received):
                items = received if isinstance(received, list) else [received]
                assert len(items) == 2, f"Expected 2 calls (recognize, teacher), got {len(items)}"

            ollama.assert_call(
                run=lambda url: consume(url),
                validate=validate,
                responses=[
                    # recognize: no ability matches
                    [{"message": {"content": '{"impression": "cannot place this", "ability": 0}'}, "done": True}],
                    # teacher: names existing meaning "chatting"
                    [{"message": {"content": '{"existing": "chatting"}'}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
