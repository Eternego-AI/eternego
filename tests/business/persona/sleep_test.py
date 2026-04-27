from application.platform.processes import on_separate_process_async

async def test_sleep_succeeds():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents
        from application.core.brain.pulse import Pulse
        from application.core.brain.signals import Tick
        from application.platform import ollama
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        def run(url):
            outcome = asyncio.run(spec.create(
                name="SleepBot", thinking=Model(name="llama3", url=url), channels=[Channel(type="web", credentials={})],
            ))
            assert outcome.success, outcome.message
            persona_id = outcome.data.persona.id
            outcome = asyncio.run(spec.find(persona_id))
            persona = outcome.data.persona
            class FakeWorker:
                def run(self, *a, **kw): pass
                def nudge(self): pass
                async def settle(self, timeout=None): pass
                async def stop(self): pass
            pulse = Pulse(FakeWorker())
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=pulse, ego=ego, eye=eye, consultant=consultant, teacher=teacher)

            # Plant a signal that represents the day's felt sense — sleep should
            # close it out so the new day starts on a fresh stream.
            day_signal = Tick("realize", {"persona": persona})
            living.signals.append(day_signal)
            assert day_signal in living.signals, "marker signal should be present before sleep"

            outcome = asyncio.run(spec.sleep(ego, living))
            assert outcome.success, outcome.message
            assert day_signal not in living.signals, \
                "sleep should clear the day's signals from living"

        ollama.assert_call(
            run=run,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
