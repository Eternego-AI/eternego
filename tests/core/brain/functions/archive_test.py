"""Archive stage — integration tests over a real Living.

Archive runs at night (it's only on the NIGHT cycle in Living.phase) after
reflect has moved messages to the archive. It walks the archived batches
looking for vision tool-call pairs and writes a gallery JSONL so
recall_history can surface past images.
"""

from application.platform.processes import on_separate_process_async


async def test_archive_records_vision_call_in_gallery():
    """At night, a vision tool-call + TOOL_RESULT pair in the archive becomes a
    gallery entry with source / question / answer."""
    def isolated():
        import asyncio, os, tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.pulse.phase = Phase.NIGHT

            living.memory.add_tool_result(
                "tools.vision",
                {"source": "/path/to/screen.png", "question": "What's open?"},
                "ok",
                "VS Code with the brain folder",
            )
            living.memory.archive_messages()
            living.memory.forget()

            consequences = asyncio.run(functions.archive(living.memory, living.ego))
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
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.pulse.phase = Phase.NIGHT

            living.memory.add_tool_result(
                "tools.look_at",
                {"source": "/screenshots/8am.png", "question": "what app?"},
                "ok",
                "browser tab",
            )
            living.memory.archive_messages()
            living.memory.forget()

            asyncio.run(functions.archive(living.memory, living.ego))

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
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.pulse.phase = Phase.NIGHT

            living.memory.add_tool_result(
                "tools.vision",
                {"source": "/missing.png"},
                "error",
                "",
            )
            living.memory.archive_messages()
            living.memory.forget()

            asyncio.run(functions.archive(living.memory, living.ego))
            assert not paths.gallery(persona.id).exists(), "no gallery entry on empty answer"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_archive_skips_screenshots_taken_by_persona():
    """Screenshots from the take_screenshot / screen abilities live under
    the persona's screenshots/ dir. They're working memory for the
    screen-control loop, not material the persona's gallery should keep."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain.memory import Memory
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
            living = agents.Living(pulse=Pulse(FakeWorker(), ego.persona), ego=ego, memory=Memory(ego.persona), eye=eye, consultant=consultant, teacher=teacher)
            living.pulse.phase = Phase.NIGHT

            shot_path = str(paths.screenshots(persona.id) / "20260517090000.png")
            living.memory.add_tool_result(
                "tools.vision",
                {"source": shot_path, "question": "what's on screen?"},
                "ok",
                "the pycharm window",
            )
            living.memory.archive_messages()
            living.memory.forget()

            asyncio.run(functions.archive(living.memory, living.ego))
            assert not paths.gallery(persona.id).exists(), \
                "gallery should not record self-taken screenshots"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


