"""Clock — single-pass cycle runner with executor.

Each test constructs a real Living with a controlled cycle (mocked async
steps), runs `clock.run(living)`, and asserts on what dispatched, what was
recorded in memory, and which steps ran.
"""

from application.platform.processes import on_separate_process_async


async def test_clean_cycle_runs_every_step():
    """A cycle whose steps all return [] runs to completion in order."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import clock
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform.asyncio_worker import Worker

            ran = []
            async def step(name):
                ran.append(name)
                return []

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(Worker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.cycle = [
                ("realize", lambda: step("realize")),
                ("recognize", lambda: step("recognize")),
                ("decide", lambda: step("decide")),
            ]

            asyncio.run(clock.run(living))
            assert ran == ["realize", "recognize", "decide"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_engine_connection_error_dispatches_brain_fault_and_halts():
    """A step raising EngineConnectionError dispatches a BrainFault carrying
    persona/provider/url/model_name/error, and the next step does not run."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import clock
            from application.core.brain.pulse import Pulse
            from application.core.brain.signals import BrainFault
            from application.core.data import Model, Persona
            from application.core.exceptions import EngineConnectionError
            from application.platform import observer
            from application.platform.asyncio_worker import Worker

            ran = []
            faulty_model = Model(name="qwen3:32b", url="http://localhost:11434")

            async def ok():
                ran.append("realize")
                return []

            async def faulty():
                ran.append("recognize")
                raise EngineConnectionError("empty response", model=faulty_model)

            async def should_not_run():
                ran.append("decide")
                return []

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(Worker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.cycle = [
                ("realize", lambda: ok()),
                ("recognize", lambda: faulty()),
                ("decide", lambda: should_not_run()),
            ]

            faults = []
            def capture(signal: BrainFault):
                faults.append(signal)
            observer.subscribe(capture)

            asyncio.run(clock.run(living))

            assert ran == ["realize", "recognize"]
            assert len(faults) == 1
            f = faults[0]
            assert f.title == "recognize"
            assert f.details["persona"] is persona
            assert f.details["provider"] == "ollama"
            assert f.details["url"] == "http://localhost:11434"
            assert f.details["model_name"] == "qwen3:32b"
            assert "empty response" in f.details["error"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_run_exits_immediately_when_worker_stopped():
    """If the worker is stopped before run, no step executes."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import clock
            from application.core.brain.pulse import Pulse
            from application.core.data import Model, Persona
            from application.platform.asyncio_worker import Worker

            ran = []
            async def step():
                ran.append(1)
                return []

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            worker = Worker()
            worker._stopped = True
            living = agents.Living(pulse=Pulse(worker), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.cycle = [("realize", lambda: step())]

            asyncio.run(clock.run(living))
            assert ran == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_executor_runs_ability_consequence_and_records():
    """When a step returns [{"abilities.<name>": {...}}], the executor calls
    the ability, records add_tool_result with the result, and dispatches a
    CapabilityRun signal."""
    def isolated():
        import asyncio, os, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents, paths
            from application.core.brain import clock
            from application.core.brain.pulse import Pulse
            from application.core.brain.signals import CapabilityRun
            from application.core.data import Model, Persona
            from application.platform import observer
            from application.platform.asyncio_worker import Worker

            async def step():
                return [{"abilities.save_notes": {"content": "remember this"}}]

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(Worker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.cycle = [("decide", lambda: step())]

            runs = []
            def capture(signal: CapabilityRun):
                runs.append(signal)
            observer.subscribe(capture)

            asyncio.run(clock.run(living))

            # Notes file got written
            assert paths.notes(persona.id).read_text().strip() == "remember this"
            # Memory has the call/result pair
            msgs = ego.memory.messages
            assert len(msgs) == 2
            assert msgs[0].prompt.role == "assistant"
            assert "abilities.save_notes" in msgs[0].content
            assert msgs[1].prompt.role == "user"
            assert "TOOL_RESULT" in msgs[1].content
            assert "notes updated" in msgs[1].content
            # CapabilityRun dispatched with the right shape
            assert len(runs) == 1
            assert runs[0].title == "abilities.save_notes"
            assert runs[0].details["status"] == "ok"
            assert runs[0].details["result"] == "notes updated"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_executor_records_error_when_ability_raises():
    """An ability raising an exception → executor catches, status='error',
    result is the exception text, still recorded in memory and dispatched."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import clock
            from application.core.brain.pulse import Pulse
            from application.core.brain.signals import CapabilityRun
            from application.core.data import Model, Persona
            from application.platform import observer
            from application.platform.asyncio_worker import Worker

            async def step():
                # save_notes raises ValueError when content is empty
                return [{"abilities.save_notes": {"content": ""}}]

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(Worker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.cycle = [("decide", lambda: step())]

            runs = []
            def capture(signal: CapabilityRun):
                runs.append(signal)
            observer.subscribe(capture)

            asyncio.run(clock.run(living))

            msgs = ego.memory.messages
            assert len(msgs) == 2
            assert "TOOL_RESULT" in msgs[1].content
            assert "status: error" in msgs[1].content
            assert "content is required" in msgs[1].content
            assert len(runs) == 1
            assert runs[0].details["status"] == "error"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_executor_runs_tool_consequence_and_records():
    """When a step returns [{"tools.<name>": {...}}], the executor calls
    tools.call (which already returns (status, result)) and records the pair."""
    def isolated():
        import asyncio, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import clock
            from application.core.brain.pulse import Pulse
            from application.core.brain.signals import CapabilityRun
            from application.core.data import Model, Persona
            from application.platform import observer
            from application.platform.asyncio_worker import Worker

            async def step():
                return [{"tools.OS.execute_on_sub_process": {"command": "echo hello-clock"}}]

            persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
            ego = agents.Ego(persona)
            eye = agents.Eye(persona)
            consultant = agents.Consultant(persona)
            teacher = agents.Teacher(persona)
            living = agents.Living(pulse=Pulse(Worker()), ego=ego, eye=eye, consultant=consultant, teacher=teacher)
            living.cycle = [("decide", lambda: step())]

            runs = []
            def capture(signal: CapabilityRun):
                runs.append(signal)
            observer.subscribe(capture)

            asyncio.run(clock.run(living))

            msgs = ego.memory.messages
            assert len(msgs) == 2
            assert "tools.OS.execute_on_sub_process" in msgs[0].content
            assert "TOOL_RESULT" in msgs[1].content
            assert "hello-clock" in msgs[1].content
            assert len(runs) == 1
            assert runs[0].title == "tools.OS.execute_on_sub_process"
            assert runs[0].details["status"] == "ok"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
