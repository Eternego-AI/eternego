from datetime import datetime, timezone

from application.platform.datetimes import stamp, date_stamp, from_stamp, iso_8601


async def test_it_formats_compact_timestamp():
    dt = datetime(2026, 3, 15, 14, 30, 45)
    assert stamp(dt) == "20260315143045"


async def test_it_formats_date_stamp():
    dt = datetime(2026, 3, 15, 14, 30, 45)
    assert date_stamp(dt) == "2026-03-15"


async def test_it_parses_compact_timestamp():
    result = from_stamp("20260315143045")
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 15
    assert result.hour == 14
    assert result.minute == 30
    assert result.second == 45


async def test_it_roundtrips_stamp():
    dt = datetime(2026, 1, 1, 0, 0, 0)
    text = stamp(dt)
    back = from_stamp(text)
    assert back.year == dt.year
    assert back.month == dt.month
    assert back.day == dt.day
    assert back.hour == dt.hour


async def test_it_formats_iso_8601():
    dt = datetime(2026, 3, 15, 14, 30, 45, tzinfo=timezone.utc)
    result = iso_8601(dt)
    assert "2026-03-15" in result
    assert "14:30:45" in result
