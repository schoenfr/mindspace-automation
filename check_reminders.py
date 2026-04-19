#!/usr/bin/env python3
"""
mindspace reminder checker

Entry point. Scans all markdown files in the Obsidian vault for due reminders
and fires macOS notifications via terminal-notifier.
"""

import logging
from datetime import datetime
from pathlib import Path

import src.config as config
import src.frontmatter as frontmatter
import src.notifier as notifier
import src.overview as overview
import src.recurrence as recurrence


def _vault_rel(path: Path) -> str:
    """Return vault-relative path without .md extension, for Obsidian deep links."""
    return str(path.relative_to(config.VAULT_ROOT)).replace(".md", "")


def process_file(path: Path, now: datetime) -> overview.ReminderEntry | None:
    """Process a single markdown file.

    Fires a notification if a reminder is due, updates frontmatter accordingly,
    and returns a ReminderEntry if the file has an upcoming reminder — so the
    caller can build the overview without re-reading files from disk.
    """
    text = path.read_text(encoding="utf-8")
    fields, body = frontmatter.parse(text)

    if not fields:
        return None

    remind_at_str     = fields.get("remind_at")
    last_reminded_str = fields.get("last_reminded_at")
    recur_str         = fields.get("recur")
    sound             = fields.get("sound", config.DEFAULT_SOUND)
    color             = fields.get("color", config.DEFAULT_COLOR)
    message           = body.split("\n")[0] if body else ""

    if not remind_at_str and not recur_str:
        return None  # not a reminder file

    # ── Recurring ─────────────────────────────────────────────────────────────
    if recur_str:
        rrule = recurrence.to_rrule(recur_str)
        if not rrule:
            return None

        most_recent = recurrence.most_recent_occurrence(rrule, now)
        if not most_recent:
            return None  # pattern hasn't had a past occurrence yet

        last_reminded = frontmatter.parse_dt(last_reminded_str) if last_reminded_str else None
        should_fire   = last_reminded is None or last_reminded < most_recent

        if not should_fire:
            if not remind_at_str:
                next_occ = recurrence.next_occurrence_after(rrule, now)
                if next_occ:
                    fields["remind_at"] = next_occ.strftime(config.DATETIME_FMT)
                    frontmatter.write(path, fields, body)
            # Fall through to build entry from existing remind_at
        else:
            notifier.fire(path.stem, message or recur_str, sound, _vault_rel(path), color)
            logging.info(f"Fired recurring reminder: {path.name}")

            fields["last_reminded_at"] = now.strftime(config.DATETIME_FMT)
            next_occ = recurrence.next_occurrence_after(rrule, now)
            if next_occ:
                fields["remind_at"] = next_occ.strftime(config.DATETIME_FMT)
            frontmatter.write(path, fields, body)

        remind_at = frontmatter.parse_dt(fields.get("remind_at", ""))
        if not remind_at:
            return None
        return overview.ReminderEntry(
            remind_at=remind_at,
            title=path.stem,
            message=message,
            recur=recur_str,
            vault_rel=_vault_rel(path),
        )

    # ── One-shot ──────────────────────────────────────────────────────────────
    remind_at = frontmatter.parse_dt(remind_at_str)
    if not remind_at:
        logging.warning(f"Could not parse remind_at in {path.name}: {remind_at_str!r}")
        return None

    if remind_at > now:
        # Not due yet — still upcoming
        return overview.ReminderEntry(
            remind_at=remind_at,
            title=path.stem,
            message=message,
            recur=None,
            vault_rel=_vault_rel(path),
        )

    if frontmatter.parse_dt(last_reminded_str) is not None:
        return None  # already fired, nothing upcoming

    notifier.fire(path.stem, message or remind_at_str, sound, _vault_rel(path), color)
    logging.info(f"Fired one-shot reminder: {path.name}")

    fields["last_reminded_at"] = now.strftime(config.DATETIME_FMT)
    frontmatter.write(path, fields, body)
    return None  # fired, so no longer upcoming


if __name__ == "__main__":
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info("check-reminders started")
    now = datetime.now()

    md_files = [
        p for p in config.VAULT_ROOT.rglob("*.md")
        if ".obsidian" not in p.parts
    ]
    logging.info(f"Scanning {len(md_files)} files")

    entries: list[overview.ReminderEntry] = []
    for path in md_files:
        try:
            entry = process_file(path, now)
            if entry is not None:
                entries.append(entry)
        except Exception as e:
            logging.error(f"Error processing {path.name}: {e}")

    try:
        overview.write_overview(entries, now)
    except Exception as e:
        logging.error(f"Failed to generate overview: {e}")
