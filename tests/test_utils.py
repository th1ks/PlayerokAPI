from __future__ import annotations

from datetime import datetime, timezone

import pytest

from PlayerokAPI.common.utils import (
    drop_none,
    format_path,
    parse_datetime,
    to_float,
    unwrap_envelope,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-10-03T08:50:15Z", datetime(2026, 10, 3, 8, 50, 15, tzinfo=timezone.utc)),
        ("2026-08-21T00:00:00.000Z", datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)),
        ("2026-10-03T08:50:15+00:00", datetime(2026, 10, 3, 8, 50, 15, tzinfo=timezone.utc)),
        (1759481415, datetime.fromtimestamp(1759481415, tz=timezone.utc)),
        (1759481415000, datetime.fromtimestamp(1759481415, tz=timezone.utc)),
    ],
)
def test_parse_datetime(raw: object, expected: datetime) -> None:
    assert parse_datetime(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "не дата", [], {}])
def test_parse_datetime_tolerates_garbage(raw: object) -> None:
    assert parse_datetime(raw) is None


def test_drop_none() -> None:
    assert drop_none({"a": 1, "b": None, "c": False}) == {"a": 1, "c": False}


def test_format_path() -> None:
    assert format_path("/item/{id}/republish", {"id": "a b"}) == "/item/a%20b/republish"
    assert format_path("/user-geo", None) == "/user-geo"


def test_format_path_missing_param() -> None:
    with pytest.raises(KeyError):
        format_path("/item/{id}", {})


def test_unwrap_envelope() -> None:
    assert unwrap_envelope({"success": True, "data": 42}) == 42
    assert unwrap_envelope({"country": "NL"}) == {"country": "NL"}
    # «data» рядом с посторонними ключами — это не конверт
    assert unwrap_envelope({"data": 1, "total": 2}) == {"data": 1, "total": 2}


def test_to_float() -> None:
    assert to_float("1.5") == 1.5
    assert to_float(None) is None
    assert to_float("x", 0.0) == 0.0
