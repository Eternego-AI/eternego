from application.platform.processes import on_separate_process_async

async def test_feed_succeeds_with_anthropic_data():
    def isolated():
        import tempfile
        import os
        import json
        import asyncio
        from application.core import agents
        from application.core.brain.pulse import Pulse
        from application.business import persona as spec
        from application.platform import ollama
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        def run(url):
            outcome = asyncio.run(spec.create(
                name="FeedBot", thinking=Model(name="llama3", url=url), channels=[Channel(type="web", credentials={})],
            ))
            assert outcome.success, outcome.message
            persona_id = outcome.data.persona.id
            outcome = asyncio.run(spec.find(persona_id))
            persona = outcome.data.persona

            class FakeWorker:
                def run(self, *args): pass
                def nudge(self): pass
                async def stop(self): pass
            pulse = Pulse(FakeWorker())
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=pulse, ego=ego, eye=eye, consultant=consultant, teacher=teacher)

            data = json.dumps([
                {"chat_messages": [
                    {"sender": "human", "text": "I like Python"},
                    {"sender": "assistant", "text": "Great choice"},
                ]}
            ])
            messages_before = len(living.ego.memory.messages)
            outcome = asyncio.run(spec.feed(living, data, "claude"))
            assert outcome.success, outcome.message
            # The fed-data intro should have landed on the live persona's memory
            # as a user-role message, framed with the source label.
            new_messages = living.ego.memory.messages[messages_before:]
            fed_intro = [m for m in new_messages if "fed data from claude" in (m.content or "")]
            assert fed_intro, f"expected fed-data intro in memory, got {[m.content for m in new_messages]!r}"

        ollama.assert_call(
            run=run,
            response={"message": {"content": '{"context": "Person likes Python.", "identity": [], "traits": [], "wishes": [], "struggles": [], "persona_traits": [], "permissions": []}'}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


