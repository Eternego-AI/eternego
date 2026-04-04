from application.platform.processes import on_separate_process_async


# ── verify ───────────────────────────────────────────────────────────────────

async def test_verify_sets_channel_name_and_verified_at():
    def isolated():
        import os
        import tempfile
        from application.core import channels, gateways, paths
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))
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
        from application.core import channels, gateways
        from application.core.data import Channel
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
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
        from application.core import channels, gateways
        from application.core.data import Channel

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
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
        from application.core import channels, gateways
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))
        received = []

        class FakeBus:
            async def put(self, text):
                received.append(text)

        ch1 = Channel(type="web", name="w1", bus=FakeBus())
        ch2 = Channel(type="web", name="w2", bus=FakeBus())
        gateways.of(p).add(ch1, {"type": "manual"})
        gateways.of(p).add(ch2, {"type": "manual"})

        asyncio.run(channels.send_all(p, "broadcast"))

        assert len(received) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── express_thinking ─────────────────────────────────────────────────────────

async def test_express_thinking_sends_typing_to_telegram_channels():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.core import channels, gateways
        from application.core.data import Channel, Model, Persona
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))
        ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})
        gateways.of(p).add(ch, {"type": "manual"})

        def assert_equal(actual, expected):
            assert actual == expected, f"Expected {expected}, got {actual}"

        telegram.assert_typing_action(
            run=lambda: asyncio.run(channels.express_thinking(p)),
            validate=lambda r: assert_equal(r["body"]["action"], "typing"),
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_express_thinking_skips_non_telegram_channels():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.core import channels, gateways
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))

        class FakeBus:
            async def put(self, text): pass

        ch = Channel(type="web", name="w1", bus=FakeBus())
        gateways.of(p).add(ch, {"type": "manual"})

        asyncio.run(channels.express_thinking(p))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── keep_open ────────────────────────────────────────────────────────────────

async def test_keep_open_returns_polling_strategy_for_telegram():
    def isolated():
        import os
        import tempfile
        from application.core import channels, gateways
        from application.core.data import Channel, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))
        ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})

        strategy = channels.keep_open(p, ch)

        assert strategy["type"] == "polling"
        assert callable(strategy["connection"])

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_keep_open_connection_returns_messages_from_poll():
    def isolated():
        import os
        import tempfile
        from application.core import channels, gateways
        from application.core.data import Channel, Message, Model, Persona
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))
        ch = Channel(type="telegram", name="", credentials={"token": "fake-token"})

        strategy = channels.keep_open(p, ch)

        def assert_equal(actual, expected):
            assert actual == expected, f"Expected {expected}, got {actual}"

        def assert_messages(messages, expected_count):
            assert len(messages) == expected_count, f"Expected {expected_count} messages, got {len(messages)}"
            for msg in messages:
                assert isinstance(msg, Message)

        telegram.assert_call(
            run=lambda: assert_messages(strategy["connection"](), expected_count=1),
            validate=lambda r: assert_equal(r["path"], "/botfake-token/getUpdates"),
            response={"result": [
                {"update_id": 100, "message": {"text": "hello", "chat": {"id": 123, "type": "private"}, "message_id": 1}}
            ]},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_keep_open_connection_filters_group_without_mention():
    def isolated():
        import os
        import tempfile
        from application.core import channels, gateways
        from application.core.data import Channel, Message, Model, Persona
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))
        ch = Channel(type="telegram", name="", credentials={"token": "fake-token"})

        strategy = channels.keep_open(p, ch)

        def assert_messages(messages, expected_count):
            assert len(messages) == expected_count, f"Expected {expected_count} messages, got {len(messages)}"
            for msg in messages:
                assert isinstance(msg, Message)

        telegram.assert_call(
            run=lambda: assert_messages(strategy["connection"](), expected_count=0),
            response={"result": [
                {"update_id": 100, "message": {"text": "not for bot", "chat": {"id": 123, "type": "group"}, "message_id": 1}}
            ]},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_keep_open_raises_on_unsupported_channel():
    def isolated():
        import os
        import tempfile
        from application.core import channels, gateways
        from application.core.data import Channel, Model, Persona
        from application.core.exceptions import ChannelError

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        gateways._active.clear()
        p = Persona(id="test-ch", name="Primus", model=Model(name="llama3"))

        try:
            channels.keep_open(p, Channel(type="unknown", name="x"))
            assert False, "should have raised"
        except ChannelError as e:
            assert "Unsupported" in str(e)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
