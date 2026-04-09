"""is_local — local vs remote model detection."""

from application.platform.processes import on_separate_process_async


async def test_returns_true_for_no_provider():
    def isolated():
        from application.core import models
        from application.core.data import Model
        assert models.is_local(Model(name="llama3", url="not required")) is True
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_returns_false_for_anthropic():
    def isolated():
        from application.core import models
        from application.core.data import Model
        assert models.is_local(Model(name="claude-3", provider="anthropic", credentials={"api_key": "k"}, url="not required")) is False
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_returns_false_for_openai():
    def isolated():
        from application.core import models
        from application.core.data import Model
        assert models.is_local(Model(name="gpt-4", provider="openai", credentials={"api_key": "k"}, url="not required")) is False
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
