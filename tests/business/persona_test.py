import os
import json
import tempfile
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from application.business import persona as spec
from application.core import agents, gateways, paths
from application.core.data import Channel, Message, Model, Persona
from application.core.brain.data import Meaning
from application.platform import ollama
import config.inference as cfg


_original_home = os.environ.get("HOME")


class FakeWorker:
    def __init__(self):
        self.stopped = False
        self.nudged = 0
    def run(self, *args): pass
    def nudge(self): self.nudged += 1


class TestMeaning(Meaning):
    name = "Test"
    def description(self): return "Test"
    def clarify(self): return None
    def reply(self): return "Reply"
    def path(self): return None
    def summarize(self): return None


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp
    agents._personas.clear()
    gateways._active.clear()
    return tmp


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home
    agents._personas.clear()
    gateways._active.clear()


def _persona(id="test-persona", name="Primus"):
    return Persona(id=id, name=name, model=Model(name="llama3"), base_model="llama3")


def _save_persona(p):
    from application.platform import objects, filesystem
    identity = paths.persona_identity(p.id)
    identity.parent.mkdir(parents=True, exist_ok=True)
    filesystem.write_json(identity, objects.json(p))


def _register_persona(p):
    _save_persona(p)
    home = paths.home(p.id)
    for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
        (home / f).touch()
    ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
    agents._personas[p.id] = ego
    return ego


def _fake_ollama_server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            path = self.path
            if path == "/api/chat":
                self.wfile.write(json.dumps({"message": {"content": "ok"}}).encode())
            elif path == "/api/generate":
                self.wfile.write(json.dumps({"response": "ok"}).encode())
            else:
                self.wfile.write(json.dumps({"status": "success"}).encode())
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "eternego-test"}]}).encode())
        def do_DELETE(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{}')
        def log_message(self, *a): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _with_fake_ollama(fn):
    server = _fake_ollama_server()
    port = server.server_address[1]
    original_cfg = cfg.OLLAMA_BASE_URL
    original_mod = ollama.OLLAMA_BASE_URL
    cfg.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"
    ollama.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"
    try:
        return fn()
    finally:
        cfg.OLLAMA_BASE_URL = original_cfg
        ollama.OLLAMA_BASE_URL = original_mod
        server.shutdown()


# ── get_list ─────────────────────────────────────────────────────────────────

def test_get_list_returns_empty_when_no_personas():
    _setup()
    result = asyncio.run(spec.get_list())
    assert result.success is False
    assert result.data["personas"] == []
    _teardown()


def test_get_list_returns_personas():
    _setup()
    _save_persona(_persona())
    result = asyncio.run(spec.get_list())
    assert result.success is True
    assert len(result.data["personas"]) == 1
    _teardown()


# ── find ─────────────────────────────────────────────────────────────────────

def test_find_returns_persona():
    _setup()
    p = _persona()
    _save_persona(p)
    result = asyncio.run(spec.find(p.id))
    assert result.success is True
    assert result.data["persona"].name == "Primus"
    _teardown()


def test_find_fails_when_not_found():
    _setup()
    result = asyncio.run(spec.find("nonexistent"))
    assert result.success is False
    _teardown()


# ── loaded ───────────────────────────────────────────────────────────────────

def test_loaded_returns_running_persona():
    _setup()
    p = _persona()
    _register_persona(p)
    result = asyncio.run(spec.loaded(p.id))
    assert result.success is True
    _teardown()


def test_loaded_fails_when_not_running():
    _setup()
    result = asyncio.run(spec.loaded("not-running"))
    assert result.success is False
    _teardown()


# ── conversation ─────────────────────────────────────────────────────────────

def test_conversation_returns_messages():
    _setup()
    p = _persona()
    conv_path = paths.conversation(p.id)
    conv_path.parent.mkdir(parents=True, exist_ok=True)
    conv_path.write_text(
        json.dumps({"role": "person", "content": "hello"}) + "\n"
        + json.dumps({"role": "persona", "content": "hi"}) + "\n"
    )
    result = asyncio.run(spec.conversation(p.id))
    assert result.success is True
    assert len(result.data["messages"]) == 2
    _teardown()


def test_conversation_returns_empty_when_no_file():
    _setup()
    result = asyncio.run(spec.conversation("no-conv"))
    assert result.success is True
    assert result.data["messages"] == []
    _teardown()


# ── running ──────────────────────────────────────────────────────────────────

def test_running_returns_registered_personas():
    _setup()
    _register_persona(_persona())
    result = asyncio.run(spec.running())
    assert result.success is True
    assert len(result.data["personas"]) == 1
    _teardown()


# ── pair ─────────────────────────────────────────────────────────────────────

def test_pair_generates_code():
    _setup()
    p = _persona()
    p.channels = [Channel(type="telegram", name="")]
    _register_persona(p)
    result = asyncio.run(spec.pair(p, Channel(type="telegram", name="12345")))
    assert result.success is True
    assert len(result.data["pairing_code"]) == 6
    _teardown()


def test_pair_fails_when_already_verified():
    _setup()
    result = asyncio.run(spec.pair(_persona(), Channel(type="telegram", name="x", verified_at="2026-03-15")))
    assert result.success is False
    _teardown()


def test_pair_fails_when_channel_not_on_persona():
    _setup()
    p = _persona()
    p.channels = []
    result = asyncio.run(spec.pair(p, Channel(type="telegram", name="x")))
    assert result.success is False
    _teardown()


# ── hear ─────────────────────────────────────────────────────────────────────

def test_hear_succeeds():
    _setup()
    p = _persona()
    _register_persona(p)
    result = asyncio.run(spec.hear(p, Message(channel=Channel(type="web", name="w1"), content="hello")))
    assert result.success is True
    _teardown()


# ── disconnect ───────────────────────────────────────────────────────────────

def test_disconnect_succeeds():
    _setup()
    p = _persona()
    ch = Channel(type="web", name="w1")
    gateways.of(p).add(ch, {"type": "web"})
    result = asyncio.run(spec.disconnect(p, ch))
    assert result.success is True
    _teardown()


# ── query ────────────────────────────────────────────────────────────────────

def test_query_returns_response():
    _setup()
    p = _persona()
    _register_persona(p)
    result = {}
    ollama.assert_call(
        run=lambda: _capture(result, spec.query(p, {"role": "user", "content": "hi"})),
        response={"message": {"content": "Hello from the model"}},
    )
    assert result["value"].success is True
    assert result["value"].data["response"] == "Hello from the model"
    _teardown()


# ── oversee ──────────────────────────────────────────────────────────────────

def test_oversee_returns_persona_knowledge():
    _setup()
    p = _persona()
    _register_persona(p)
    paths.save_as_string(paths.person_identity(p.id), "The person lives in Amsterdam.")
    result = asyncio.run(spec.oversee(p))
    assert result.success is True
    assert "person" in result.data
    _teardown()


# ── create ───────────────────────────────────────────────────────────────────

def test_create_succeeds():
    _setup()
    result = _with_fake_ollama(lambda: asyncio.run(spec.create(
        name="TestBot",
        model="llama3",
        channel_type="web",
        channel_credentials={},
    )))
    assert result.success is True, f"Create failed: {result.message}"
    assert result.data["name"] == "TestBot"
    assert len(result.data["recovery_phrase"].split()) == 24
    _teardown()


def test_create_with_frontier_succeeds():
    _setup()
    result = _with_fake_ollama(lambda: asyncio.run(spec.create(
        name="FrontierBot",
        model="llama3",
        channel_type="web",
        channel_credentials={},
        frontier_model="claude-3-opus-20240229",
        frontier_provider="anthropic",
        frontier_credentials={"api_key": "test-key"},
    )))
    assert result.success is True, f"Create failed: {result.message}"
    _teardown()


# ── delete ───────────────────────────────────────────────────────────────────

def test_delete_succeeds():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="DeleteMe", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        find_result = asyncio.run(spec.find(create_result.data["persona_id"]))
        return asyncio.run(spec.delete(find_result.data["persona"]))

    result = _with_fake_ollama(run)
    assert result.success is True
    _teardown()


# ── write_diary ──────────────────────────────────────────────────────────────

def test_write_diary_succeeds():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="DiaryBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]

        find_result = asyncio.run(spec.find(persona_id))
        persona = find_result.data["persona"]

        return asyncio.run(spec.write_diary(persona))

    result = _with_fake_ollama(run)
    assert result.success is True
    _teardown()


# ── migrate ──────────────────────────────────────────────────────────────────

def test_migrate_restores_persona_from_diary():
    _setup()

    def run():
        # 1. Create persona
        create_result = asyncio.run(spec.create(
            name="MigrateMe", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        phrase = create_result.data["recovery_phrase"]

        # 2. Write diary (already done during create, but let's do it explicitly)
        find_result = asyncio.run(spec.find(persona_id))
        persona = find_result.data["persona"]
        diary_result = asyncio.run(spec.write_diary(persona))
        assert diary_result.success is True

        # 3. Get diary file path
        diary_file = paths.diary(persona_id) / f"{persona_id}.diary"
        assert diary_file.exists(), f"Diary file not found at {diary_file}"

        # 4. Delete persona
        delete_result = asyncio.run(spec.delete(persona))
        assert delete_result.success is True

        # 5. Migrate using diary and recovery phrase
        return asyncio.run(spec.migrate(str(diary_file), phrase, "llama3"))

    result = _with_fake_ollama(run)
    assert result.success is True, f"Migrate failed: {result.message}"
    assert "persona_id" in result.data
    assert result.data["name"] == "MigrateMe"
    _teardown()


# ── control ──────────────────────────────────────────────────────────────────

def test_control_removes_person_identity_entry():
    _setup()
    p = _persona()
    _register_persona(p)
    paths.save_as_string(paths.person_identity(p.id), "The person lives in Amsterdam.\nThe person is a developer.")

    # Get entry IDs via oversee
    oversee_result = asyncio.run(spec.oversee(p))
    entries = oversee_result.data["person"]
    amsterdam_id = entries[0]["id"]

    result = asyncio.run(spec.control(p, [amsterdam_id]))
    assert result.success is True
    assert result.data["removed"] == 1

    # Verify it was removed via oversee
    after = asyncio.run(spec.oversee(p))
    assert len(after.data["person"]) == 1
    _teardown()


def test_control_fails_on_invalid_id_format():
    _setup()
    p = _persona()
    _register_persona(p)
    result = asyncio.run(spec.control(p, ["noprefixhere"]))
    assert result.success is False
    _teardown()


# ── live ─────────────────────────────────────────────────────────────────────

def test_live_processes_due_destiny_entries():
    _setup()
    p = _persona()
    _register_persona(p)

    # Create a destiny entry that is due now
    from datetime import datetime, timedelta
    from application.platform import datetimes
    now = datetimes.now()
    past = now - timedelta(minutes=5)
    paths.save_destiny_entry(p.id, "reminder", past.strftime("%Y-%m-%d %H:%M"), "Call the dentist")

    result = asyncio.run(spec.live(p, now))
    assert result.success is True
    assert "1" in result.message
    _teardown()


def test_live_returns_nothing_due_when_empty():
    _setup()
    p = _persona()
    _register_persona(p)

    from application.platform import datetimes
    result = asyncio.run(spec.live(p, datetimes.now()))
    assert result.success is True
    assert "Nothing due" in result.message
    _teardown()


# ── nap ──────────────────────────────────────────────────────────────────────

def test_nap_succeeds():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="NapBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        find_result = asyncio.run(spec.find(persona_id))
        return asyncio.run(spec.nap(find_result.data["persona"]))

    result = _with_fake_ollama(run)
    assert result.success is True
    _teardown()


# ── sleep ────────────────────────────────────────────────────────────────────

def test_sleep_succeeds():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="SleepBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        find_result = asyncio.run(spec.find(persona_id))
        return asyncio.run(spec.sleep(find_result.data["persona"]))

    # sleep calls learn_from_experience (ollama), grow (ollama + fine-tune), write_diary, wake
    # All ollama calls go to our fake server. grow will fail (no DNA) but that's OK — it logs warning.
    result = _with_fake_ollama(run)
    assert result.success is True
    _teardown()


# ── wake ─────────────────────────────────────────────────────────────────────

def test_wake_succeeds():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="WakeBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]

        # Nap first to unload
        find_result = asyncio.run(spec.find(persona_id))
        asyncio.run(spec.nap(find_result.data["persona"]))

        # Wake
        from application.platform.asyncio_worker import Worker
        return asyncio.run(spec.wake(persona_id, Worker()))

    result = _with_fake_ollama(run)
    assert result.success is True
    _teardown()


# ── feed ─────────────────────────────────────────────────────────────────────

def test_feed_succeeds_with_anthropic_data():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="FeedBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        find_result = asyncio.run(spec.find(persona_id))
        persona = find_result.data["persona"]

        data = json.dumps([
            {"chat_messages": [
                {"sender": "human", "text": "I like Python"},
                {"sender": "assistant", "text": "Great choice"},
            ]}
        ])
        return asyncio.run(spec.feed(persona, data, "claude"))

    # feed calls frontier.read (pure parsing) then ego.learn (ollama for subconscious)
    result = _with_fake_ollama(run)
    assert result.success is True, f"Feed failed: {result.message}"
    _teardown()


# ── connect ──────────────────────────────────────────────────────────────────

def test_connect_web_channel_succeeds():
    _setup()

    def run():
        create_result = asyncio.run(spec.create(
            name="ConnectBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        find_result = asyncio.run(spec.find(persona_id))
        persona = find_result.data["persona"]
        ch = Channel(type="web", name="new-web")
        return asyncio.run(spec.connect(persona, ch))

    result = _with_fake_ollama(run)
    assert result.success is True
    _teardown()



async def _capture(result, coro):
    result["value"] = await coro
