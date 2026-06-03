from __future__ import annotations

from datetime import date, timedelta

from scripts.fetch_latest import latest_default_end_date


def test_latest_default_end_date_is_yesterday():
    assert latest_default_end_date() == date.today() - timedelta(days=1)
