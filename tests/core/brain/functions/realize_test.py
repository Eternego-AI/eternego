"""Realize stage — integration tests over a real Living.

Realize surveys what just landed in memory and brings it in. Plain text gets a
string prompt; images take one of two paths — inline content blocks (no vision
model) or vision-tool roundtrip (consultant formulates questions, eye answers).
"""

from application.platform.processes import on_separate_process_async


async def test_realize_plain_text_sets_user_prompt():
    """A message with no media gets a simple Prompt(role='user', content=<text>).
    No model call. No new messages added. Returns []."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            ego.memory.remember(Message(content="hello"))
            messages_before = len(ego.memory.messages)

            consequences = asyncio.run(functions.realize(living))

            assert consequences == []
            assert len(ego.memory.messages) == messages_before
            assert ego.memory.messages[-1].prompt is not None
            assert ego.memory.messages[-1].prompt.role == "user"
            assert ego.memory.messages[-1].prompt.content == "hello"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_skips_already_realized_messages():
    """If a message already has a prompt, realize leaves it alone — no rework."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            existing = Prompt(role="user", content="already there")
            ego.memory.remember(Message(content="hi", prompt=existing))

            consequences = asyncio.run(functions.realize(living))

            assert consequences == []
            assert ego.memory.messages[-1].prompt is existing

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_image_without_vision_inlines_content_blocks():
    """When persona has no vision model, the image is inlined as content blocks
    (text + image source) directly in the prompt — the thinking model sees it."""
    def isolated():
        import asyncio, os, tempfile, base64
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Media, Message, Model, Persona

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            image_path = Path(tmp) / "shot.png"
            image_path.write_bytes(b"\x89PNG fake bytes")

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            ego.memory.remember(Message(
                content="caption!",
                media=Media(source=str(image_path), caption="caption!"),
            ))
            messages_before = len(ego.memory.messages)

            consequences = asyncio.run(functions.realize(living))

            assert consequences == []
            assert len(ego.memory.messages) == messages_before
            prompt = ego.memory.messages[-1].prompt
            assert prompt is not None
            assert isinstance(prompt.content, list)
            kinds = [b.get("type") for b in prompt.content]
            assert "image" in kinds
            assert "text" in kinds

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_image_missing_path_records_error_tool_result():
    """If the image file was deleted between hear/see and realize, the prompt
    falls back to the caption and an error TOOL_RESULT is added so the persona
    sees what went wrong."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Media, Message, Model, Persona

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(
                id="t", name="T",
                thinking=Model(name="m", url="not used"),
                vision=Model(name="v", url="not used"),
            )
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            ego.memory.remember(Message(
                content="caption",
                media=Media(source="/no/such/file.png", caption="caption"),
            ))
            messages_before = len(ego.memory.messages)

            consequences = asyncio.run(functions.realize(living))

            assert consequences == []
            assert len(ego.memory.messages) == messages_before + 2
            call_msg = ego.memory.messages[-2]
            assert call_msg.prompt.role == "assistant"
            assert "tools.vision" in call_msg.content
            error_msg = ego.memory.messages[-1].content
            assert "TOOL_RESULT" in error_msg
            assert "vision" in error_msg
            assert "error" in error_msg
            original_prompt = ego.memory.messages[-3].prompt
            assert original_prompt is not None
            assert original_prompt.content == "caption"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_image_with_vision_records_call_and_result():
    """With a vision model: consultant formulates questions, eye answers, and
    realize records the pair as (assistant: vision call, user: TOOL_RESULT)."""
    def isolated():
        import os, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Media, Message, Model, Persona
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            image_path = Path(tmp) / "shot.png"
            image_path.write_bytes(b"\x89PNG fake bytes")

            async def consume(url):
                persona = Persona(
                    id="t", name="T",
                    thinking=Model(name="m", url=url),
                    vision=Model(name="v", url=url),
                )
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.remember(Message(
                    content="what's on screen?",
                    media=Media(source=str(image_path), caption="what's on screen?"),
                ))
                msgs_before = len(ego.memory.messages)

                consequences = await functions.realize(living)

                assert consequences == []
                assert len(ego.memory.messages) == msgs_before + 2
                call = ego.memory.messages[-2]
                assert call.prompt.role == "assistant"
                assert "tools.vision" in call.content
                assert "what is here" in call.content.lower() or "describe" in call.content.lower()
                result = ego.memory.messages[-1]
                assert result.prompt.role == "user"
                assert "TOOL_RESULT" in result.content
                assert "a green square" in result.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": '{"questions": ["What is here?"]}'}, "done": True}],
                    [{"message": {"content": "a green square"}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_question_formulation_failure_uses_default():
    """If the consultant returns invalid JSON, realize falls back to a default
    question ('Describe what you see.') and still calls the eye — never blocks."""
    def isolated():
        import os, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.pulse import Pulse
            from application.core.data import Media, Message, Model, Persona
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            image_path = Path(tmp) / "shot.png"
            image_path.write_bytes(b"\x89PNG fake bytes")

            async def consume(url):
                persona = Persona(
                    id="t", name="T",
                    thinking=Model(name="m", url=url),
                    vision=Model(name="v", url=url),
                )
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                ego.memory.remember(Message(
                    content="caption",
                    media=Media(source=str(image_path), caption="caption"),
                ))

                await functions.realize(living)
                call = ego.memory.messages[-2]
                assert "Describe what you see" in call.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": "no json here"}, "done": True}],
                    [{"message": {"content": "ok answer"}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
