from application.platform.processes import on_separate_process_async

async def test_feed_succeeds_with_anthropic_data():
    def isolated():
        import tempfile
        import os
        import json
        import asyncio
        from application.core import agents, gateways
        from application.business import persona as spec
        from application.platform import ollama
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()

        def run(url):
            outcome = asyncio.run(spec.create(
                name="FeedBot", thinking=Model(name="llama3", url=url), channel=Channel(type="web", credentials={}),
            ))
            assert outcome.success, outcome.message
            persona_id = outcome.data["persona_id"]
            outcome = asyncio.run(spec.find(persona_id))
            persona = outcome.data["persona"]

            data = json.dumps([
                {"chat_messages": [
                    {"sender": "human", "text": "I like Python"},
                    {"sender": "assistant", "text": "Great choice"},
                ]}
            ])
            outcome = asyncio.run(spec.feed(persona, data, "claude"))
            assert outcome.success, outcome.message

        ollama.assert_call(
            run=run,
            response={"message": {"content": "ok"}}
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


