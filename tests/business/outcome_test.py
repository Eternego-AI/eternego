from application.business.outcome import Outcome


def test_it_creates_successful_outcome():
    result = Outcome(success=True, message="done")
    assert result.success is True
    assert result.message == "done"
    assert result.data is None


def test_it_creates_outcome_with_data():
    result = Outcome(success=True, message="ok", data={"key": "value"})
    assert result.data == {"key": "value"}


def test_it_creates_failed_outcome():
    result = Outcome(success=False, message="something went wrong")
    assert result.success is False
    assert result.message == "something went wrong"
