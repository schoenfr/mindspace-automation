"""
mindspace reminder overview

Generates a structured Markdown overview of all upcoming reminders in the
Obsidian vault, grouped by time horizon (Today / This Week / Later).
Called by check_reminders.py after each scan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import config
import frontmatter


@dataclass
class _ReminderEntry:
    remind_at: datetime
    title: str          # file stem
    message: str        # first body line
    recur: str | None   # natural-language recurrence string, if any
    vault_rel: str      # vault-relative path without .md, for wiki links


def _vault_rel(path: Path) -> str:
    """Return vault-relative path without .md extension, for Obsidian wiki links."""
    return str(path.relative_to(config.VAULT_ROOT)).replace(".md", "")


def _collect_upcoming(files: list[Path], now: datetime) -> list[_ReminderEntry]:
    """
    Scan all markdown files and return entries for reminders that are
    upcoming (remind_at > now) and not yet fired for one-shot reminders.
    Recurring reminders always carry a precomputed remind_at in their
    frontmatter (written by check_reminders), so they are handled uniformly.
    """
    entries: list[_ReminderEntry] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
            fields, body = frontmatter.parse(text)
        except Exception as e:
            logging.warning(f"overview: could not read {path.name}: {e}")
            continue

        if not fields:
            continue

        remind_at_str     = fields.get("remind_at")
        last_reminded_str = fields.get("last_reminded_at")
        recur_str         = fields.get("recur")

        # Must have a future remind_at to appear in the overview
        if not remind_at_str:
            continue

        remind_at = frontmatter.parse_dt(remind_at_str)
        if remind_at is None or remind_at <= now:
            continue

        # One-shot reminders that already fired are excluded
        if not recur_str and last_reminded_str:
            continue

        message = body.split("\n")[0].strip() if body else ""

        entries.append(_ReminderEntry(
            remind_at=remind_at,
            title=path.stem,
            message=message,
            recur=recur_str,
            vault_rel=_vault_rel(path),
        ))

    entries.sort(key=lambda e: e.remind_at)
    return entries


def _bucket(remind_at: datetime, now: datetime) -> str:
    """Return the section heading for a reminder datetime."""
    today_date = now.date()
    end_of_week = today_date.isocalendar()  # (year, week, weekday)

    if remind_at.date() == today_date:
        return "Today"

    # Same ISO year+week counts as "this week"
    if remind_at.isocalendar()[:2] == now.isocalendar()[:2]:
        return "This Week"

    return "Later"


def _format_entry(entry: _ReminderEntry, now: datetime) -> str:
    """Format a single reminder as a Markdown list item."""
    today_date = now.date()

    if entry.remind_at.date() == today_date:
        time_str = entry.remind_at.strftime("%H:%M")
    elif entry.remind_at.isocalendar()[:2] == now.isocalendar()[:2]:
        time_str = entry.remind_at.strftime("%a %d %b, %H:%M")
    else:
        time_str = entry.remind_at.strftime("%Y-%m-%d %H:%M")

    label = entry.message or entry.title
    link  = f"[[{entry.vault_rel}|{entry.title}]]"
    recur = f" *({entry.recur})*" if entry.recur else ""

    return f"- {time_str} — {label} {link}{recur}"


def write_overview(files: list[Path], now: datetime) -> None:
    """
    Build and write the Reminders overview Markdown file.
    Called once per check_reminders.py run, after all files are processed.
    """
    entries = _collect_upcoming(files, now)

    # Group into ordered sections
    section_order = ["Today", "This Week", "Later"]
    sections: dict[str, list[str]] = {s: [] for s in section_order}

    for entry in entries:
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
        logging.info(f"Overview written: {len(entries)} upcoming reminder(s)")
    except Exception as e:
        logging.error(f"Failed to write overview: {e}")
