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


async def test_text_cycle_reflect_moves_messages_to_archive():
    """Full text cycle: realize → recognize → decide → experience → reflect.
    When reflect returns no leftover, messages move to archive and active
    messages are cleared."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import situation
            from application.core.brain.functions import decide, experience, realize, recognize, wondering, reflect
            from application.core.brain.mind.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="reflect-test",
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
                ego.pulse.situation = situation.normal

                assert await realize(ego, ego.perspective(), memory) is True
                assert await recognize(ego, ego.personality(), memory) is True
                assert await wondering(ego, ego.teacher(), memory) is True
                assert await decide(ego, ego.personality(), memory) is True
                assert await experience(ego, ego.personality(), memory) is True

                messages_before = len(memory.messages)
                assert messages_before > 0

                assert await reflect(ego, ego.personality(), memory) is True

                assert len(memory.messages) == 0, "Messages should be cleared after reflect"
                assert len(memory.archive) == 1, "One batch should be in archive"
                assert len(memory.archive[0]) == messages_before, "Archived batch should have all messages"
                assert memory.context is not None and memory.context != ""

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": '{"impression": "greeting", "ability": 1}'}, "done": True}],
                    [{"message": {"content": '{"tool": "say", "text": "Hello!"}'}, "done": True}],
                    [{"message": {"content": '{"context": "Person said hi, I greeted back.", "leftover": ""}'}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_reflect_leftover_keeps_messages_and_restarts():
    """When reflect returns a leftover, messages stay in active memory,
    context is unchanged, and reflect returns False."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import situation
            from application.core.brain.functions import reflect
            from application.core.brain.mind.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="leftover-test",
                    name="Pipe",
                    thinking=Model(name="llama3", url=url),
                    base_model="llama3",
                )
                paths.home(persona.id).mkdir(parents=True, exist_ok=True)

                memory = Memory(persona)
                memory.remember(Message(
                    content="Do something",
                    prompt=Prompt(role="user", content="Do something"),
                ))
                original_context = memory.context

                ego = agents.Ego(persona, FakeWorker())
                ego.pulse.situation = situation.normal

                result = await reflect(ego, ego.personality(), memory)
                assert result is False, "Reflect should return False when there is leftover"
                assert len(memory.messages) == 2, "Original message + leftover should be in memory"
                assert memory.messages[-1].prompt.role == "assistant"
                assert memory.messages[-1].prompt.content == "I need to finish this task"
                assert len(memory.archive) == 0, "No archive when leftover"
                assert memory.context == original_context, "Context unchanged on leftover"

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": '{"context": "Person asked to do something.", "leftover": "I need to finish this task"}'}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_image_with_vision_model_produces_tool_result():
    """When an image arrives and persona has a vision model, realize formulates
    questions via thinking model, calls the vision model, and adds a vision
    tool-call + TOOL_RESULT pair. The original message gets the caption as prompt."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from pathlib import Path
            from application.core import agents, paths
            from application.core.brain.functions import realize
            from application.core.brain.mind.memory import Memory
            from application.core.data import Media, Message, Model, Persona
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume(url):
                persona = Persona(
                    id="vision-test",
                    name="Pipe",
                    thinking=Model(name="llama3", url=url),
                    vision=Model(name="llava", url=url),
                    base_model="llama3",
                )
                paths.home(persona.id).mkdir(parents=True, exist_ok=True)

                image_path = Path(tmp) / "test.jpg"
                image_path.write_bytes(b"\xff\xd8\xff\xe0test image data")

                memory = Memory(persona)
                memory.remember(Message(
                    content="What is this?",
                    media=Media(source=str(image_path), caption="What is this?"),
                ))

                ego = agents.Ego(persona, FakeWorker())
                result = await realize(ego, ego.perspective(), memory)
                assert result is True

                assert memory.messages[0].prompt is not None, "Original message should have prompt set"
                assert memory.messages[0].prompt.content == "What is this?", "Prompt should be the caption"
                assert memory.messages[0].prompt.role == "user"

                assert len(memory.messages) == 3, f"Expected 3 messages (original + vision call + result), got {len(memory.messages)}"
                assert memory.messages[1].prompt.role == "assistant"
                assert '"tool": "vision"' in memory.messages[1].prompt.content
                assert memory.messages[2].prompt.role == "user"
                assert memory.messages[2].prompt.content.startswith("TOOL_RESULT")
                assert "a beautiful flower" in memory.messages[2].prompt.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    # thinking model: question formulation
                    [{"message": {"content": '{"questions": ["What type of flower is this?"]}'}, "done": True}],
                    # vision model: image description
                    [{"message": {"content": "a beautiful flower in a garden"}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_image_without_vision_model_inlines_content_blocks():
    """When an image arrives and persona has no vision model, realize encodes
    the image as base64 content blocks in the prompt. The thinking model sees
    the image inline."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from pathlib import Path
            from application.core import agents, paths
            from application.core.brain.functions import realize
            from application.core.brain.mind.memory import Memory
            from application.core.data import Media, Message, Model, Persona

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            async def consume():
                persona = Persona(
                    id="inline-test",
                    name="Pipe",
                    thinking=Model(name="llama3", url="http://unused"),
                    base_model="llama3",
                )
                paths.home(persona.id).mkdir(parents=True, exist_ok=True)

                image_path = Path(tmp) / "photo.png"
                image_path.write_bytes(b"\x89PNG\r\n\x1a\ntest")

                memory = Memory(persona)
                memory.remember(Message(
                    content="Look at this",
                    media=Media(source=str(image_path), caption="Look at this"),
                ))

                ego = agents.Ego(persona, FakeWorker())
                result = await realize(ego, ego.perspective(), memory)
                assert result is True

                prompt = memory.messages[0].prompt
                assert prompt is not None
                assert isinstance(prompt.content, list), "Content should be a list of content blocks"
                assert len(prompt.content) == 2, "Should have image block + text block"
                assert prompt.content[0]["type"] == "image"
                assert prompt.content[0]["source"]["type"] == "base64"
                assert prompt.content[0]["source"]["media_type"] == "image/png"
                assert prompt.content[1]["type"] == "text"
                assert prompt.content[1]["text"] == "Look at this"

                assert len(memory.messages) == 1, "No extra messages added (no vision call)"

            import asyncio
            asyncio.run(consume())

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
