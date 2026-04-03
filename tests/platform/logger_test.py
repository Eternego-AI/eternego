import json
import tempfile
from pathlib import Path

from application.platform.logger import Level, Message, log, file_media


def test_message_has_id_and_level():
    msg = Message("test event", {"key": "val"}, Level.INFO)
    assert msg.id
    assert msg.time > 0
    assert msg.title == "test event"
    assert msg.level == Level.INFO


def test_file_media_writes_json_log():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "test.log"
        media = file_media(path)
        msg = Message("something happened", {"user": "alice"}, Level.WARNING)
        media(msg)

        content = path.read_text().strip()
        entry = json.loads(content)
        assert entry["title"] == "something happened"
        assert entry["level"] == "warning"
        assert entry["context"]["user"] == "alice"
        assert "id" in entry
        assert "time" in entry


def test_file_media_appends_multiple_entries():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "test.log"
        media = file_media(path)
        media(Message("first", {}, Level.INFO))
        media(Message("second", {}, Level.DEBUG))

        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2


def test_log_dispatches_to_provided_media():
    received = []

    def fake_media(msg):
        received.append(msg.title)

    msg = Message("dispatch test", {}, Level.INFO)
    log(msg, fake_media)
    assert received == ["dispatch test"]


def test_file_media_with_callable_path():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "dynamic.log"
        media = file_media(lambda: path)
        media(Message("dynamic", {}, Level.INFO))
        assert path.exists()
        entry = json.loads(path.read_text().strip())
        assert entry["title"] == "dynamic"
