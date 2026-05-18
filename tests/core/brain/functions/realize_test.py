"""Realize stage — integration tests over a real Living.

Realize surveys what just landed in memory and brings it in. Plain text
gets a string prompt; images always go through the eye, with two
sub-paths: (1) the media already carries a question (set by the ability
that produced it — take_screenshot, screen, look_at) and the consultant
is skipped, or (2) the media has no question (e.g., an external image
from hear/see) and the consultant formulates one text-only first.
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
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.memory.remember(Message(content="hello"))
            messages_before = len(living.memory.messages)

            consequences = asyncio.run(functions.realize(living.memory, living.ego, living.eye, living.consultant))

            assert consequences == []
            assert len(living.memory.messages) == messages_before
            assert living.memory.messages[-1].prompt is not None
            assert living.memory.messages[-1].prompt.role == "user"
            assert living.memory.messages[-1].prompt.content == "hello"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_skips_already_realized_messages():
    """If a message already has a prompt, realize leaves it alone — no rework."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            existing = Prompt(role="user", content="already there")
            living.memory.remember(Message(content="hi", prompt=existing))

            consequences = asyncio.run(functions.realize(living.memory, living.ego, living.eye, living.consultant))

            assert consequences == []
            assert living.memory.messages[-1].prompt is existing

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_image_without_vision_falls_back_to_thinking():
    """When persona has no vision model, realize uses the thinking model as
    eye — the message's prompt is text-only (caption) and a vision tool-call
    pair is added with the answer. No image blocks ever live in a prompt."""
    def isolated():
        import asyncio, json, os, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
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
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.remember(Message(
                    content="caption!",
                    media=Media(source=str(image_path), caption="caption!"),
                ))

                await functions.realize(living.memory, living.ego, living.eye, living.consultant)

                msgs = living.memory.messages
                # original message: prompt is text-only (the caption)
                original = msgs[0]
                assert original.prompt is not None
                assert original.prompt.content == "caption!"
                # followed by a tools.vision call + TOOL_RESULT pair
                assert any(m.prompt and "tools.vision" in str(m.prompt.content) for m in msgs[1:])
                tool_result = next(m for m in msgs if m.prompt and isinstance(m.prompt.content, str) and m.prompt.content.startswith("TOOL_RESULT"))
                assert "fake answer" in tool_result.prompt.content

            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": json.dumps({"questions": ["q1"]})}, "done": True}],
                    [{"message": {"content": "fake answer"}, "done": True}],
                ],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_skips_consultant_when_media_carries_question():
    """When the media already has a question (set by take_screenshot,
    screen, or look_at), realize asks the eye directly — no consultant
    formulation step, only one model call instead of two."""
    def isolated():
        import asyncio, os, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain.memory import Memory
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
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.remember(Message(
                    content="screenshot",
                    media=Media(
                        source=str(image_path),
                        caption="screenshot",
                        question="I clicked at (300, 400). What's the effect?",
                    ),
                ))

                await functions.realize(living.memory, living.ego, living.eye, living.consultant)

                msgs = living.memory.messages
                tool_result = next(m for m in msgs if m.prompt and isinstance(m.prompt.content, str) and m.prompt.content.startswith("TOOL_RESULT"))
                assert "the dialog opened" in tool_result.prompt.content
                # Check the recorded vision call carries the original question.
                vision_call = next(m for m in msgs if m.prompt and m.prompt.role == "assistant" and "tools.vision" in str(m.prompt.content))
                assert "I clicked at (300, 400)" in vision_call.prompt.content

            # Only ONE model call expected — no consultant — the eye answer.
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[
                    [{"message": {"content": "the dialog opened"}, "done": True}],
                ],
            )

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
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.memory.remember(Message(
                content="caption",
                media=Media(source="/no/such/file.png", caption="caption"),
            ))
            messages_before = len(living.memory.messages)

            consequences = asyncio.run(functions.realize(living.memory, living.ego, living.eye, living.consultant))

            assert consequences == []
            assert len(living.memory.messages) == messages_before + 2
            call_msg = living.memory.messages[-2]
            assert call_msg.prompt.role == "assistant"
            assert "tools.vision" in call_msg.content
            error_msg = living.memory.messages[-1].content
            assert "TOOL_RESULT" in error_msg
            assert "vision" in error_msg
            assert "error" in error_msg
            original_prompt = living.memory.messages[-3].prompt
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
            from application.core.brain.memory import Memory
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
                living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.remember(Message(
                    content="what's on screen?",
                    media=Media(source=str(image_path), caption="what's on screen?"),
                ))
                msgs_before = len(living.memory.messages)

                consequences = await functions.realize(living.memory, living.ego, living.eye, living.consultant)

                assert consequences == []
                assert len(living.memory.messages) == msgs_before + 2
                call = living.memory.messages[-2]
                assert call.prompt.role == "assistant"
                assert "tools.vision" in call.content
                assert "what is here" in call.content.lower() or "describe" in call.content.lower()
                result = living.memory.messages[-1]
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
            from application.core.brain.memory import Memory
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
                living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
                living.memory.remember(Message(
                    content="caption",
                    media=Media(source=str(image_path), caption="caption"),
                ))

                await functions.realize(living.memory, living.ego, living.eye, living.consultant)
                call = living.memory.messages[-2]
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
