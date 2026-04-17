from application.platform.processes import on_separate_process_async


async def test_connect_web_returns_passive_strategy():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business.persona import connect
        from application.core.data import Channel, Model, Persona

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"))
        ch = Channel(type="web", name="w1")

        outcome = asyncio.run(connect(p, ch))
        assert outcome.success, outcome.message
        assert outcome.data.channel.type == "web"
        assert outcome.data.poll is None
        assert callable(outcome.data.close)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_connect_telegram_returns_polling_strategy():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business.persona import connect
        from application.core.data import Channel, Model, Persona

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"))
        ch = Channel(type="telegram", name="", credentials={"token": "fake"})

        outcome = asyncio.run(connect(p, ch))
        assert outcome.success, outcome.message
        assert outcome.data.channel.type == "telegram"
        assert callable(outcome.data.poll)
        assert callable(outcome.data.close)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_connect_fails_on_unsupported_channel():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business.persona import connect
        from application.core.data import Channel, Model, Persona

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"))
        ch = Channel(type="unknown", name="x")

        outcome = asyncio.run(connect(p, ch))
        assert outcome.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
