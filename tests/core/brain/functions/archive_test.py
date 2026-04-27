"""Archive stage — integration tests over a real Living.

Archive runs at night after reflect has moved messages to the archive. It
walks the archived batches looking for vision tool-call pairs and writes a
gallery JSONL so recall_history can surface past images.
"""

from application.platform.processes import on_separate_process_async


async def test_archive_skips_during_day():
    """Archive only runs at night. During day, it returns [] without writing."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
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
            living.pulse.phase = Phase.DAY
            ego.memory.remember(Message(
                content='{"tools.vision": {"source": "/x.png", "question": "?"}}',
                prompt=Prompt(role="assistant", content='{"tools.vision": {"source": "/x.png", "question": "?"}}'),
            ))
            ego.memory.archive_messages()
            ego.memory.forget()

            consequences = asyncio.run(functions.archive(living))
            assert consequences == []
            assert not paths.gallery(persona.id).exists(), "gallery should not be written during day"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_archive_records_vision_call_in_gallery():
    """At night, a vision tool-call + TOOL_RESULT pair in the archive becomes a
    gallery entry with source / question / answer."""
    def isolated():
        import asyncio, os, tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
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
            living.pulse.phase = Phase.NIGHT

            ego.memory.add_tool_result(
                "tools.vision",
                {"source": "/path/to/screen.png", "question": "What's open?"},
                "ok",
                "VS Code with the brain folder",
            )
            ego.memory.archive_messages()
            ego.memory.forget()

            consequences = asyncio.run(functions.archive(living))
            assert consequences == []

            gallery_file = paths.gallery(persona.id)
            assert gallery_file.exists(), "gallery should be written"
            entry = json.loads(gallery_file.read_text().strip().splitlines()[0])
            assert entry["source"] == "/path/to/screen.png"
            assert entry["question"] == "What's open?"
            assert entry["answer"] == "VS Code with the brain folder"
            assert "time" in entry

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_archive_records_look_at_call_in_gallery():
    """An `abilities.look_at` call is also indexed in the gallery."""
    def isolated():
        import asyncio, os, tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
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
            living.pulse.phase = Phase.NIGHT

            ego.memory.add_tool_result(
                "abilities.look_at",
                {"source": "/screenshots/8am.png", "question": "what app?"},
                "ok",
                "browser tab",
            )
            ego.memory.archive_messages()
            ego.memory.forget()

            asyncio.run(functions.archive(living))

            entry = json.loads(paths.gallery(persona.id).read_text().strip().splitlines()[0])
            assert entry["source"] == "/screenshots/8am.png"
            assert entry["answer"] == "browser tab"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_archive_skips_failed_vision_call():
    """If the TOOL_RESULT had no result line (or was an error), archive skips —
    no gallery entry for failed calls."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
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
            living.pulse.phase = Phase.NIGHT

            ego.memory.add_tool_result(
                "tools.vision",
                {"source": "/missing.png"},
                "error",
                "",
            )
            ego.memory.archive_messages()
            ego.memory.forget()

            asyncio.run(functions.archive(living))
            assert not paths.gallery(persona.id).exists(), "no gallery entry on empty answer"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_archive_describes_inline_image_at_night():
    """For images that were inlined (no vision model — image content blocks in
    the prompt), archive asks the thinking model to describe what was seen and
    saves the description to the gallery."""
    def isolated():
        import os, tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import functions
            from application.core.brain.pulse import Phase, Pulse
            from application.core.data import Media, Message, Model, Persona, Prompt
            from application.platform import ollama

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            image_path = Path(tmp) / "shot.png"
            image_path.write_bytes(b"\x89PNG fake")

            async def consume(url):
                persona = Persona(id="t", name="T", thinking=Model(name="m", url=url))
                ego = agents.Ego(persona)
                eye = agents.Eye(persona)
                consultant = agents.Consultant(persona)
                teacher = agents.Teacher(persona)
                living = agents.Living(pulse=Pulse(FakeWorker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
                living.pulse.phase = Phase.NIGHT

                inline_blocks = [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "FAKE=="}},
                    {"type": "text", "text": "what is here?"},
                ]
                ego.memory.remember(Message(
                    content="what is here?",
                    media=Media(source=str(image_path), caption="what is here?"),
                    prompt=Prompt(role="user", content=inline_blocks),
                ))
                ego.memory.archive_messages()
                ego.memory.forget()

                await functions.archive(living)

                gallery_file = paths.gallery(persona.id)
                assert gallery_file.exists()
                entry = json.loads(gallery_file.read_text().strip().splitlines()[0])
                assert entry["answer"] == "a fake png screenshot"
                assert entry["source"] == str(image_path)

            response = json.dumps({"description": "a fake png screenshot"})
            ollama.assert_call(
                run=lambda url: consume(url),
                responses=[[{"message": {"content": response}, "done": True}]],
            )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
