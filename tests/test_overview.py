"""
Tests for overview.py — pins current behaviour of _bucket and _format_entry
before the double-read / _vault_rel refactor.
"""

from datetime import datetime

import pytest

from src.overview import ReminderEntry, _bucket, _format_entry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    """Fixed reference point: Wednesday 2026-04-22 10:00."""
    return datetime(2026, 4, 22, 10, 0)


def _entry(remind_at: datetime, recur: str | None = None) -> ReminderEntry:
    return ReminderEntry(
        remind_at=remind_at,
        title="Test Note",
        message="This is a message",
        recur=recur,
        vault_rel="Some/Folder/Test Note",
    )


# ── _bucket ───────────────────────────────────────────────────────────────────

class TestBucket:
    def test_same_day_is_today(self):
        now = _now()
        remind_at = datetime(2026, 4, 22, 14, 30)
        assert _bucket(remind_at, now) == "Today"

    def test_same_day_earlier_time_is_today(self):
        now = _now()
        remind_at = datetime(2026, 4, 22, 8, 0)
        assert _bucket(remind_at, now) == "Today"

    def test_tomorrow_same_week_is_this_week(self):
        now = _now()  # Wednesday
        remind_at = datetime(2026, 4, 23, 9, 0)  # Thursday
        assert _bucket(remind_at, now) == "This Week"

    def test_end_of_same_week_is_this_week(self):
        now = _now()  # Wednesday ISO week 17
        remind_at = datetime(2026, 4, 26, 12, 0)  # Sunday same week
        assert _bucket(remind_at, now) == "This Week"

    def test_next_week_is_later(self):
        now = _now()  # ISO week 17
        remind_at = datetime(2026, 4, 27, 9, 0)  # Monday next week (week 18)
        assert _bucket(remind_at, now) == "Later"

    def test_far_future_is_later(self):
        now = _now()
        remind_at = datetime(2026, 12, 31, 23, 59)
        assert _bucket(remind_at, now) == "Later"


# ── _format_entry ─────────────────────────────────────────────────────────────

class TestFormatEntry:
    def test_today_shows_time_only(self):
        now = _now()
        entry = _entry(datetime(2026, 4, 22, 14, 30))
        result = _format_entry(entry, now)
        assert result.startswith("- 14:30")
        assert "[[Some/Folder/Test Note|Test Note]]" in result

    def test_this_week_shows_weekday_and_date(self):
        now = _now()
        entry = _entry(datetime(2026, 4, 23, 9, 0))  # Thursday
        result = _format_entry(entry, now)
        assert result.startswith("- Thu 23 Apr, 09:00")

    def test_later_shows_full_date(self):
        now = _now()
        entry = _entry(datetime(2026, 4, 27, 9, 0))
        result = _format_entry(entry, now)
        assert result.startswith("- 2026-04-27 09:00")

    def test_message_shown_as_label(self):
        now = _now()
        entry = _entry(datetime(2026, 4, 22, 14, 30))
        result = _format_entry(entry, now)
        assert "This is a message" in result

    def test_title_used_as_label_when_no_message(self):
        now = _now()
        entry = ReminderEntry(
            remind_at=datetime(2026, 4, 22, 14, 30),
            title="Test Note",
            message="",
            recur=None,
            vault_rel="Some/Folder/Test Note",
        )
        result = _format_entry(entry, now)
        assert "Test Note" in result

    def test_recur_shown_in_italics(self):
        now = _now()
        entry = _entry(datetime(2026, 4, 22, 14, 30), recur="every friday at 09:00")
        result = _format_entry(entry, now)
        assert "*(every friday at 09:00)*" in result

    def test_no_recur_annotation_when_one_shot(self):
        now = _now()
        entry = _entry(datetime(2026, 4, 22, 14, 30), recur=None)
        result = _format_entry(entry, now)
        assert "*(" not in result
