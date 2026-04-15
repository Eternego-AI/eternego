from application.platform.processes import on_separate_process_async


async def test_oversee_returns_persona_knowledge():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona

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
        paths.save_as_string(paths.person_identity(p.id), "The person lives in Amsterdam.")
        result = asyncio.run(spec.oversee(p))
        assert result.success, result.message
        assert result.data.person is not None

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
