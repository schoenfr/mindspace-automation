#!/usr/bin/env python3
"""
mindspace reminder checker

Entry point. Scans all markdown files in the Obsidian vault for due reminders
and fires macOS notifications via terminal-notifier.
"""

import logging
from datetime import datetime
from pathlib import Path

import config
import frontmatter
import notifier
import recurrence


def _vault_rel(path: Path) -> str:
    """Return vault-relative path without .md extension, for Obsidian deep links."""
    return str(path.relative_to(config.VAULT_ROOT)).replace(".md", "")


def process_file(path: Path, now: datetime) -> None:
    text = path.read_text(encoding="utf-8")
    fields, body = frontmatter.parse(text)

    if not fields:
        return

    remind_at_str     = fields.get("remind_at")
    last_reminded_str = fields.get("last_reminded_at")
    recur_str         = fields.get("recur")
    sound             = fields.get("sound", config.DEFAULT_SOUND)
    color             = fields.get("color", config.DEFAULT_COLOR)
    message           = body.split("\n")[0] if body else ""

    if not remind_at_str and not recur_str:
        return  # not a reminder file

    # ── Recurring ─────────────────────────────────────────────────────────────
    if recur_str:
        rrule = recurrence.to_rrule(recur_str)
        if not rrule:
            return

        most_recent = recurrence.most_recent_occurrence(rrule, now)
        if not most_recent:
            return  # pattern hasn't had a past occurrence yet

        last_reminded = frontmatter.parse_dt(last_reminded_str) if last_reminded_str else None
        should_fire   = last_reminded is None or last_reminded < most_recent

        if not should_fire:
            if not remind_at_str:
                next_occ = recurrence.next_occurrence_after(rrule, now)
                if next_occ:
                    fields["remind_at"] = next_occ.strftime(config.DATETIME_FMT)
                    frontmatter.write(path, fields, body)
            return

        notifier.fire("Recurring reminder", message or recur_str, sound, _vault_rel(path), color)
        logging.info(f"Fired recurring reminder: {path.name}")

        fields["last_reminded_at"] = now.strftime(config.DATETIME_FMT)
        next_occ = recurrence.next_occurrence_after(rrule, now)
        if next_occ:
            fields["remind_at"] = next_occ.strftime(config.DATETIME_FMT)
        frontmatter.write(path, fields, body)
        return

    # ── One-shot ──────────────────────────────────────────────────────────────
    remind_at = frontmatter.parse_dt(remind_at_str)
    if not remind_at:
        logging.warning(f"Could not parse remind_at in {path.name}: {remind_at_str!r}")
        return

    if remind_at > now:
        return  # not due yet

    if frontmatter.parse_dt(last_reminded_str) is not None:
        return  # already fired

    notifier.fire("Reminder", message or remind_at_str, sound, _vault_rel(path), color)
    logging.info(f"Fired one-shot reminder: {path.name}")

    fields["last_reminded_at"] = now.strftime(config.DATETIME_FMT)
    frontmatter.write(path, fields, body)


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

    for path in md_files:
        try:
            process_file(path, now)
        except Exception as e:
            logging.error(f"Error processing {path.name}: {e}")
