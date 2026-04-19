"""
mindspace reminder overview

Generates a structured Markdown overview of all upcoming reminders in the
Obsidian vault, grouped by time horizon (Today / This Week / Later).
Called by check_reminders.py after each scan, receiving pre-collected entries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from . import config


@dataclass
class ReminderEntry:
    remind_at: datetime
    title: str          # file stem
    message: str        # first body line
    recur: str | None   # natural-language recurrence string, if any
    vault_rel: str      # vault-relative path without .md, for wiki links


def _bucket(remind_at: datetime, now: datetime) -> str:
    """Return the section heading for a reminder datetime."""
    if remind_at.date() == now.date():
        return "Today"

    # Same ISO year+week counts as "this week"
    if remind_at.isocalendar()[:2] == now.isocalendar()[:2]:
        return "This Week"

    return "Later"


def _format_entry(entry: ReminderEntry, now: datetime) -> str:
    """Format a single reminder as a Markdown list item."""
    bucket = _bucket(entry.remind_at, now)

    if bucket == "Today":
        time_str = entry.remind_at.strftime("%H:%M")
    elif bucket == "This Week":
        time_str = entry.remind_at.strftime("%a %d %b, %H:%M")
    else:
        time_str = entry.remind_at.strftime("%Y-%m-%d %H:%M")

    label = entry.message or entry.title
    link  = f"[[{entry.vault_rel}|{entry.title}]]"
    recur = f" *({entry.recur})*" if entry.recur else ""

    return f"- {time_str} — {label} {link}{recur}"


def write_overview(entries: list[ReminderEntry], now: datetime) -> None:
    """
    Build and write the Reminders overview Markdown file.
    Called once per check_reminders.py run, after all files are processed.
    Receives pre-collected, pre-filtered ReminderEntry objects.
    """
    upcoming = sorted(
        (e for e in entries if e.remind_at > now),
        key=lambda e: e.remind_at,
    )

    # Group into ordered sections
    section_order = ["Today", "This Week", "Later"]
    sections: dict[str, list[str]] = {s: [] for s in section_order}

    for entry in upcoming:
        bucket = _bucket(entry.remind_at, now)
        sections[bucket].append(_format_entry(entry, now))

    lines: list[str] = [
        f"*Updated: {now.strftime(config.DATETIME_FMT)}*",
        "",
    ]

    any_content = False
    for section in section_order:
        items = sections[section]
        if not items:
            continue
        any_content = True
        lines.append(f"## {section}")
        lines.append("")
        lines.extend(items)
        lines.append("")

    if not any_content:
        lines.append("*No upcoming reminders.*")
        lines.append("")

    output = "\n".join(lines)

    try:
        config.OVERVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.OVERVIEW_FILE.write_text(output, encoding="utf-8")
        logging.info(f"Overview written: {len(upcoming)} upcoming reminder(s)")
    except Exception as e:
        logging.error(f"Failed to write overview: {e}")
