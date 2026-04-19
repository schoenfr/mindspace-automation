"""
Tests for check_reminders.process_file — focusing on recurring reminder
behaviour, particularly that remind_at in frontmatter is ignored.
"""

import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import check_reminders
import src.config as config
from src.overview import ReminderEntry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_note(tmp_path: Path, frontmatter: dict, body: str = "A reminder") -> Path:
    path = tmp_path / "note.md"
    fields = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
    path.write_text(f"---\n{fields}\n---\n{body}\n", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def vault_root(tmp_path, monkeypatch):
    """Point VAULT_ROOT at tmp_path so _vault_rel works without the real vault."""
    monkeypatch.setattr(config, "VAULT_ROOT", tmp_path)
    monkeypatch.setattr(check_reminders.config, "VAULT_ROOT", tmp_path)


# ── Recurring: remind_at is ignored ──────────────────────────────────────────

class TestOneShotNoLastReminded:
    def test_does_not_crash_when_last_reminded_at_missing(self, tmp_path):
        """Regression: parse_dt(None) must not raise AttributeError."""
        path = _write_note(tmp_path, {
            "remind_at": "2026-04-19 02:39",
            # no last_reminded_at
        })
        now = datetime(2026, 4, 19, 2, 41)  # past the remind_at

        with patch("check_reminders.notifier"):
            entry = check_reminders.process_file(path, now)  # must not raise

        assert entry is None  # fired and done


class TestRecurringRemindAt:
    def test_stale_remind_at_does_not_block_firing(self, tmp_path):
        """A stale remind_at should have no effect on whether the reminder fires."""
        path = _write_note(tmp_path, {
            "recur": "every day at 09:00",
            "remind_at": "2020-01-01 09:00",   # very stale
            "last_reminded_at": "2020-01-01 09:00",
        })
        now = datetime(2026, 4, 22, 10, 0)

        with patch("check_reminders.notifier") as mock_notifier:
            check_reminders.process_file(path, now)

        mock_notifier.fire.assert_called_once()

    def test_stale_remind_at_does_not_appear_in_entry(self, tmp_path):
        """ReminderEntry.remind_at must be the live next occurrence, not the stale frontmatter value."""
        path = _write_note(tmp_path, {
            "recur": "every day at 09:00",
            "remind_at": "2020-01-01 09:00",   # very stale
            "last_reminded_at": "2020-01-01 09:00",
        })
        now = datetime(2026, 4, 22, 10, 0)

        with patch("check_reminders.notifier"):
            entry = check_reminders.process_file(path, now)

        assert entry is not None
        assert entry.remind_at != datetime(2020, 1, 1, 9, 0), \
            "remind_at on ReminderEntry should be the next occurrence, not the stale frontmatter value"
        assert entry.remind_at > now

    def test_changed_recur_reflects_new_pattern(self, tmp_path):
        """Changing recur (with stale remind_at left behind) must produce next occurrence from new pattern."""
        path = _write_note(tmp_path, {
            "recur": "every monday at 08:00",   # changed pattern
            "remind_at": "2026-04-19 09:00",    # leftover from old (e.g. every 20 minutes)
            "last_reminded_at": "2026-04-19 09:00",
        })
        now = datetime(2026, 4, 22, 10, 0)  # Wednesday

        with patch("check_reminders.notifier"):
            entry = check_reminders.process_file(path, now)

        assert entry is not None
        # Next Monday from Wednesday 2026-04-22 is 2026-04-27
        assert entry.remind_at == datetime(2026, 4, 27, 8, 0)

    def test_remind_at_not_written_to_disk_after_fire(self, tmp_path):
        """After firing, remind_at must NOT be written back to the frontmatter."""
        path = _write_note(tmp_path, {
            "recur": "every day at 09:00",
            "last_reminded_at": "2020-01-01 09:00",
        })
        now = datetime(2026, 4, 22, 10, 0)

        with patch("check_reminders.notifier"):
            check_reminders.process_file(path, now)

        content = path.read_text(encoding="utf-8")
        assert "remind_at:" not in content

    def test_remind_at_not_written_to_disk_when_not_firing(self, tmp_path):
        """Even when not firing (already up to date), remind_at must not be written."""
        path = _write_note(tmp_path, {
            "recur": "every day at 09:00",
            "last_reminded_at": "2026-04-22 09:01",  # after today's 09:00 occurrence
        })
        now = datetime(2026, 4, 22, 10, 0)

        with patch("check_reminders.notifier"):
            check_reminders.process_file(path, now)

        content = path.read_text(encoding="utf-8")
        assert "remind_at:" not in content
