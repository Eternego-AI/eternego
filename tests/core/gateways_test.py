from application.platform.processes import on_separate_process_async


async def test_add_and_all_channels():
    def isolated():
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
        conn = of(p)
        ch = Channel(type="telegram", name="123")
        conn.add(ch, {"type": "manual"})
        assert len(conn.all_channels()) == 1
        assert conn.all_channels()[0].name == "123"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_has_channel():
    def isolated():
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
        conn = of(p)
        ch = Channel(type="telegram", name="123")
        assert not conn.has_channel(ch)
        conn.add(ch, {"type": "manual"})
        assert conn.has_channel(ch)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_has_channel_matches_by_type_and_name():
    def isolated():
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
        conn = of(p)
        conn.add(Channel(type="telegram", name="123"), {"type": "manual"})
        assert conn.has_channel(Channel(type="telegram", name="123"))
        assert not conn.has_channel(Channel(type="telegram", name="456"))
        assert not conn.has_channel(Channel(type="web", name="123"))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_remove_channel():
    def isolated():
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
        conn = of(p)
        ch = Channel(type="telegram", name="123")
        conn.add(ch, {"type": "manual"})
        conn.remove(ch)
        assert len(conn.all_channels()) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_clear_removes_all():
    def isolated():
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
        conn = of(p)
        conn.add(Channel(type="telegram", name="1"), {"type": "manual"})
        conn.add(Channel(type="telegram", name="2"), {"type": "manual"})
        conn.clear()
        assert len(conn.all_channels()) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_connections_are_per_persona():
    def isolated():
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        p1 = Persona(id="p1", name="A", thinking=Model(name="llama3"))
        p2 = Persona(id="p2", name="B", thinking=Model(name="llama3"))
        of(p1).add(Channel(type="telegram", name="1"), {"type": "manual"})
        of(p2).add(Channel(type="telegram", name="2"), {"type": "manual"})
        assert len(of(p1).all_channels()) == 1
        assert len(of(p2).all_channels()) == 1
        assert of(p1).all_channels()[0].name == "1"
        assert of(p2).all_channels()[0].name == "2"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_polling_dispatches_messages_to_on_message():
    def isolated():
        import asyncio
        import time
        from application.core.gateways import of, _active
        from application.core.data import Channel, Message, Persona, Model

        _active.clear()
        received = []
        call_count = [0]
        msg = Message(channel=Channel(type="telegram", name="123"), content="hello", id="m1")

        def connection():
            call_count[0] += 1
            if call_count[0] == 1:
                return [msg]
            time.sleep(0.05)
            return []

        def on_message(m):
            received.append(m)

        async def run():
            p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
            ch = Channel(type="telegram", name="123")
            of(p).add(ch, {"type": "polling", "connection": connection, "on_message": on_message})
            await asyncio.sleep(0.2)
            of(p).clear()

        asyncio.run(run())
        assert len(received) == 1
        assert received[0].content == "hello"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_polling_stops_when_channel_removed():
    def isolated():
        import asyncio
        import time
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        call_count = [0]

        def connection():
            call_count[0] += 1
            time.sleep(0.05)
            return []

        async def run():
            p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
            ch = Channel(type="telegram", name="123")
            of(p).add(ch, {"type": "polling", "connection": connection, "on_message": lambda m: None})
            await asyncio.sleep(0.15)
            of(p).clear()
            count_at_clear = call_count[0]
            await asyncio.sleep(0.15)
            count_after = call_count[0]
            assert count_after - count_at_clear <= 1

        asyncio.run(run())

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_polling_dispatches_async_on_message():
    def isolated():
        import asyncio
        import time
        from application.core.gateways import of, _active
        from application.core.data import Channel, Message, Persona, Model

        _active.clear()
        received = []
        call_count = [0]
        msg = Message(channel=Channel(type="telegram", name="123"), content="async hello", id="m1")

        def connection():
            call_count[0] += 1
            if call_count[0] == 1:
                return [msg]
            time.sleep(0.05)
            return []

        async def on_message(m):
            received.append(m)

        async def run():
            p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
            ch = Channel(type="telegram", name="123")
            of(p).add(ch, {"type": "polling", "connection": connection, "on_message": on_message})
            await asyncio.sleep(0.3)
            of(p).clear()

        asyncio.run(run())
        assert len(received) == 1
        assert received[0].content == "async hello"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_polling_handles_connection_errors():
    def isolated():
        import asyncio
        import time
        from application.core.gateways import of, _active
        from application.core.data import Channel, Persona, Model

        _active.clear()
        call_count = [0]

        def connection():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("connection failed")
            time.sleep(0.05)
            return []

        async def run():
            p = Persona(id="test-gw", name="Primus", thinking=Model(name="llama3"))
            ch = Channel(type="telegram", name="123")
            of(p).add(ch, {"type": "polling", "connection": connection, "on_message": lambda m: None})
            await asyncio.sleep(0.2)
            of(p).clear()

        asyncio.run(run())
        assert call_count[0] > 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
