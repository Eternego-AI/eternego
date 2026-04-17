from application.platform.processes import on_separate_process_async


# ── verify ───────────────────────────────────────────────────────────────────

async def test_verify_sets_channel_name_and_verified_at():
    def isolated():
        import os
        import tempfile
        from application.core import channels, paths
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ch", name="Primus", thinking=Model(name="llama3", url="not required"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)
        paths.save_as_string(paths.persona_identity(p.id), "{}")

        ch = Channel(type="telegram", name="", credentials={"token": "t"})
        p.channels = [ch]

        channels.verify(p, ch, "12345")

        assert ch.name == "12345"
        assert ch.verified_at is not None

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── send (telegram) ─────────────────────────────────────────────────────────

async def test_send_telegram_sends_to_correct_chat():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.core import channels
        from application.core.data import Channel
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})

        def assert_equal(actual, expected):
            assert actual == expected, f"Expected {expected}, got {actual}"

        telegram.assert_send(
            run=lambda: asyncio.run(channels.send(ch, "Hello!")),
            validate=lambda r: (
                assert_equal(r["body"]["chat_id"], "12345"),
                assert_equal(r["body"]["text"], "Hello!"),
            ),
            response={"ok": True},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── send (web/bus) ───────────────────────────────────────────────────────────

async def test_send_web_puts_to_bus():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.core import channels
        from application.core.data import Channel

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        received = []

        class FakeBus:
            async def put(self, text):
                received.append(text)

        ch = Channel(type="web", name="uuid", bus=FakeBus())
        asyncio.run(channels.send(ch, "Hello from web"))

        assert received == ["Hello from web"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── send_all ─────────────────────────────────────────────────────────────────

async def test_send_all_sends_to_all_active_channels():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.core import channels
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ch", name="Primus", thinking=Model(name="llama3", url="not required"))
        received = []

        class FakeBus:
            async def put(self, text):
                received.append(text)

        ch1 = Channel(type="web", name="w1", bus=FakeBus())
        ch2 = Channel(type="web", name="w2", bus=FakeBus())

        asyncio.run(channels.send_all([ch1, ch2], "broadcast"))

        assert len(received) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── keep_open ────────────────────────────────────────────────────────────────

async def test_keep_open_returns_polling_strategy_for_telegram():
    def isolated():
        import os
        import tempfile
        from application.core import channels
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ch", name="Primus", thinking=Model(name="llama3", url="not required"))
        ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})

        strategy = channels.keep_open(p, ch)

        assert strategy["type"] == "polling"
        assert callable(strategy["connection"])

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_keep_open_connection_polls_without_error():
    def isolated():
        import os
        import tempfile
        from application.core import channels
        from application.core.data import Channel, Model, Persona
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ch", name="Primus", thinking=Model(name="llama3", url="not required"))
        ch = Channel(type="telegram", name="", credentials={"token": "fake-token"})

        strategy = channels.keep_open(p, ch)

        telegram.assert_call(
            run=lambda: strategy["connection"](),
            response={"result": [
                {"update_id": 100, "message": {"text": "hello", "chat": {"id": 123, "type": "private"}, "message_id": 1}}
            ]},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_keep_open_raises_on_unsupported_channel():
    def isolated():
        import os
        import tempfile
        from application.core import channels
        from application.core.data import Channel, Model, Persona
        from application.core.exceptions import ChannelError

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ch", name="Primus", thinking=Model(name="llama3", url="not required"))

        try:
            channels.keep_open(p, Channel(type="unknown", name="x"))
            assert False, "should have raised"
        except ChannelError as e:
            assert "Unsupported" in str(e)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
