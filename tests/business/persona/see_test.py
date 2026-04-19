from application.platform.processes import on_separate_process_async


async def test_see_succeeds_with_media():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business.persona.see import see
        from application.core import agents, paths
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        from application.platform import objects, filesystem
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        home = paths.home(p.id)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()

        image_path = os.path.join(tmp, "test_image.png")
        with open(image_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0
            def run(self, *args): pass
            def nudge(self): self.nudged += 1

        p.ego = agents.Ego(p, FakeWorker())
        channel = Channel(type="telegram", name="123", verified_at="2026-04-17T00:00:00")
        result = asyncio.run(see(p, source=image_path, caption="What is in this image?", channel=channel))
        assert result.success, result.message
        msg = p.ego.memory.messages[-1]
        assert msg.media is not None
        assert msg.media.caption == "What is in this image?"
        assert "telegram-" in msg.media.source

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_see_rejects_unverified_channel():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business.persona.see import see
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"))
        channel = Channel(type="telegram", name="123")
        result = asyncio.run(see(p, source="/tmp/img.png", caption="test", channel=channel))
        assert result.success
        assert result.data.response == "Channel not verified."

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
