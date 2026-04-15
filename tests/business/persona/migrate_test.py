from application.platform.processes import on_separate_process_async


async def test_migrate_restores_persona_from_diary():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.platform import ollama
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        def run(url):
            outcome = asyncio.run(spec.create(name="MigrateMe", thinking=Model(name="llama3", url=url), channel=Channel(type="web", credentials={})))
            assert outcome.success, outcome.message
            persona_id = outcome.data.persona.id
            phrase = outcome.data.recovery_phrase

            # 2. Write diary (already done during create, but let's do it explicitly)
            outcome = asyncio.run(spec.find(persona_id))
            persona = outcome.data.persona
            outcome = asyncio.run(spec.write_diary(persona))
            assert outcome.success, outcome.message

            # 3. Get diary file path
            diary_file = paths.diary(persona_id) / f"{persona_id}.diary"
            assert diary_file.exists(), f"Diary file not found at {diary_file}"

            # 4. Delete persona
            outcome = asyncio.run(spec.delete(persona))
            assert outcome.success, outcome.message

            # 5. Migrate using diary and recovery phrase
            outcome = asyncio.run(spec.migrate(str(diary_file), phrase, Model(name="llama3", url=url)))

            assert outcome.success, outcome.message
            assert outcome.data.persona.id
            assert outcome.data.persona.name == "MigrateMe"

        ollama.assert_call(
            run=run,
            response={"message": {"content": "ok"}}
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

