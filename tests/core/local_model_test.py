from application.core import local_model
from application.core.exceptions import EngineConnectionError, ModelError
from application.platform import ollama


def test_chat_returns_message_content():
    result = {}
    ollama.assert_post(
        run=lambda: _capture(result, local_model.chat("llama3", [{"role": "user", "content": "hi"}])),
        response={"message": {"content": "Hello!"}},
    )
    assert result["value"] == "Hello!"


def test_chat_sends_correct_payload():
    ollama.assert_post(
        run=lambda: local_model.chat("llama3", [{"role": "user", "content": "hi"}]),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/chat"),
            _assert_equal(r["body"]["model"], "llama3"),
            _assert_equal(r["body"]["messages"], [{"role": "user", "content": "hi"}]),
        ),
        response={"message": {"content": "Hello!"}},
    )


def test_chat_json_parses_json_from_response():
    result = {}
    ollama.assert_post(
        run=lambda: _capture(result, local_model.chat_json("llama3", [])),
        response={"message": {"content": '{"answer": 42}'}},
    )
    assert result["value"] == {"answer": 42}


def test_generate_returns_stripped_response():
    result = {}
    ollama.assert_post(
        run=lambda: _capture(result, local_model.generate("llama3", "prompt")),
        response={"response": "  generated text  "},
    )
    assert result["value"] == "generated text"


def test_generate_sends_to_correct_path():
    ollama.assert_post(
        run=lambda: local_model.generate("llama3", "hello"),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/generate"),
            _assert_equal(r["body"]["model"], "llama3"),
            _assert_equal(r["body"]["prompt"], "hello"),
        ),
        response={"response": "ok"},
    )


async def _capture(result, coro):
    result["value"] = await coro


def _assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
