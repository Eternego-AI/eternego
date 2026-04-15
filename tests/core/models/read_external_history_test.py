"""read_external_history — parse external AI exports."""

import json
import asyncio

from application.core import models
from application.core.exceptions import ModelError


def test_parses_anthropic_export():
    export = json.dumps([
        {"chat_messages": [{"sender": "human", "text": "Hi"}, {"sender": "assistant", "text": "Hello"}]}
    ])
    result = asyncio.run(models.read_external_history(export, "claude"))
    assert len(result) == 1
    assert result[0][0]["role"] == "user"
    assert result[0][1]["role"] == "assistant"


def test_parses_openai_export():
    export = json.dumps([
        {"mapping": {"n1": {"message": {"author": {"role": "user"}, "content": {"parts": ["Hi"]}}}}}
    ])
    result = asyncio.run(models.read_external_history(export, "openai"))
    assert len(result) == 1
    assert result[0][0]["content"] == "Hi"


def test_raises_model_error_on_invalid_anthropic_data():
    try:
        asyncio.run(models.read_external_history("not json", "claude"))
        assert False, "should have raised"
    except ModelError:
        pass


def test_raises_model_error_on_invalid_openai_data():
    try:
        asyncio.run(models.read_external_history("not json", "openai"))
        assert False, "should have raised"
    except ModelError:
        pass
