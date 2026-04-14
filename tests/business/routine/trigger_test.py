from application.platform.processes import on_separate_process_async


async def test_trigger_fires_sleep_when_due():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        current_time = datetimes.now().strftime("%H:%M")
        routines_path = paths.routines(p.id)
        routines_path.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(routines_path, {
            "routines": [
                {"spec": "sleep", "time": current_time},
            ]
        })

        fired = []
        async def sleep_by():
            fired.append(True)

        result = asyncio.run(routine.trigger(p, sleep_by))
        assert result.success, result.message
        assert "sleep" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_trigger_fires_nothing_when_no_match():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import filesystem

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        routines_path = paths.routines(p.id)
        routines_path.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(routines_path, {
            "routines": [{"spec": "sleep", "time": "99:99"}]
        })

        result = asyncio.run(routine.trigger(p, lambda: None))
        assert result.success, result.message
        assert "none" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_trigger_succeeds_when_no_routines_file():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import paths
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        result = asyncio.run(routine.trigger(p, lambda: None))
        assert result.success, result.message
        assert "none" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
