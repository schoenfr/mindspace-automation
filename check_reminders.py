#!/usr/bin/env python3
"""
mindspace reminder checker

Scans all markdown files in the Obsidian vault for due reminders and fires
macOS notifications via terminal-notifier.

Frontmatter schema:

  One-shot:
    remind_at: 2026-04-19 09:00        # absolute datetime, set by Ami
    last_reminded_at: 2026-04-19 09:02 # set by script after firing
    sound: Submarine                    # optional, default: Submarine, use "none" to suppress

  Recurring:
    recur: every friday at 17:00       # natural language pattern, set by Ami
    remind_at: 2026-04-25 17:00        # next occurrence, computed and updated by script
    last_reminded_at: 2026-04-18 17:02 # updated by script after each fire
    sound: Submarine                    # optional
"""

import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

import recurrent

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path.home() / "mindspace" / "obsidian"
LOG_FILE   = Path.home() / "mindspace" / "logs" / "reminders.log"
NOTIFIER   = "/opt/homebrew/bin/terminal-notifier"
VAULT_NAME = "obsidian"  # must match the vault name as Obsidian sees it

DATETIME_FMT = "%Y-%m-%d %H:%M"
DEFAULT_SOUND = "Submarine"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Frontmatter helpers ───────────────────────────────────────────────────────

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)
FIELD_RE       = re.compile(r"^(?P<key>\w+):\s*(?P<value>.+)$", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (fields dict, body text). Both empty/empty if no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields = {k: v.strip() for k, v in FIELD_RE.findall(m.group(1))}
    return fields, m.group(2).strip()


def write_frontmatter(path: Path, fields: dict, body: str) -> None:
    """Write updated frontmatter + body back to the file."""
    lines = "\n".join(f"{k}: {v}" for k, v in fields.items())
    path.write_text(f"---\n{lines}\n---\n{body}\n", encoding="utf-8")


def parse_dt(value: str) -> datetime | None:
    """Parse a datetime string in DATETIME_FMT. Returns None on failure."""
    try:
        return datetime.strptime(value.strip(), DATETIME_FMT)
    except ValueError:
        return None


# ── Recurrence helpers ────────────────────────────────────────────────────────

def recur_to_rrule(text: str) -> str | None:
    """Convert natural language recurrence to RRULE string."""
    r = recurrent.RecurringEvent()
    result = r.parse(text)
    if isinstance(result, str) and result.startswith("RRULE"):
        return result
    return None


def next_occurrence_after(rrule: str, after: datetime) -> datetime | None:
    """Return the next occurrence of an RRULE after a given datetime."""
    try:
        # croniter expects cron format; build a dtstart-based iterator via dateutil
        from dateutil.rrule import rrulestr
        rule = rrulestr(rrule, dtstart=after)
        return rule.after(after)
    except Exception as e:
        logging.warning(f"Failed to compute next occurrence: {e}")
        return None


def most_recent_occurrence(rrule: str, before: datetime) -> datetime | None:
    """Return the most recent past occurrence of an RRULE before a given datetime."""
    try:
        from dateutil.rrule import rrulestr
        rule = rrulestr(rrule, dtstart=datetime(2020, 1, 1))
        return rule.before(before)
    except Exception as e:
        logging.warning(f"Failed to compute most recent occurrence: {e}")
        return None


# ── Notification ──────────────────────────────────────────────────────────────

def fire_notification(title: str, message: str, sound: str, obsidian_path: str | None) -> None:
    """Fire a terminal-notifier notification."""
    args = [
        NOTIFIER,
        "-title", "mindspace",
        "-subtitle", title,
        "-message", message,
    ]
    if sound and sound.lower() != "none":
        args += ["-sound", sound]
    if obsidian_path:
        encoded = obsidian_path.replace(" ", "%20")
        args += ["-open", f"obsidian://open?vault={VAULT_NAME}&file={encoded}"]
    subprocess.run(args)


# ── Main ──────────────────────────────────────────────────────────────────────

def process_file(path: Path, now: datetime) -> None:
    text   = path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)

    if not fields:
        return

    remind_at_str      = fields.get("remind_at")
    last_reminded_str  = fields.get("last_reminded_at")
    recur_str          = fields.get("recur")
    sound              = fields.get("sound", DEFAULT_SOUND)

    if not remind_at_str and not recur_str:
        return  # not a reminder file

    # ── Recurring ─────────────────────────────────────────────────────────────
    if recur_str:
        rrule = recur_to_rrule(recur_str)
        if not rrule:
            logging.warning(f"Could not parse recur pattern in {path.name}: {recur_str!r}")
            return

        # Compute most recent past occurrence
        most_recent = most_recent_occurrence(rrule, now)
        if not most_recent:
            return  # no past occurrence yet

        last_reminded = parse_dt(last_reminded_str) if last_reminded_str else None

        # Fire if we haven't reminded since the most recent occurrence
        should_fire = (last_reminded is None) or (last_reminded < most_recent)
        if not should_fire:
            # Ensure remind_at is set to next future occurrence
            if not remind_at_str:
                next_occ = next_occurrence_after(rrule, now)
                if next_occ:
                    fields["remind_at"] = next_occ.strftime(DATETIME_FMT)
                    write_frontmatter(path, fields, body)
            return

        # Fire notification
        vault_rel = str(path.relative_to(VAULT_ROOT)).replace(".md", "")
        message = body.split("\n")[0] if body else recur_str
        fire_notification("Recurring reminder", message, sound, vault_rel)
        logging.info(f"Fired recurring reminder: {path.name}")

        # Update fields
        fields["last_reminded_at"] = now.strftime(DATETIME_FMT)
        next_occ = next_occurrence_after(rrule, now)
        if next_occ:
            fields["remind_at"] = next_occ.strftime(DATETIME_FMT)
        write_frontmatter(path, fields, body)
        return

    # ── One-shot ──────────────────────────────────────────────────────────────
    remind_at = parse_dt(remind_at_str)
    if not remind_at:
        logging.warning(f"Could not parse remind_at in {path.name}: {remind_at_str!r}")
        return

    if remind_at > now:
        return  # not due yet

    last_reminded = parse_dt(last_reminded_str) if last_reminded_str else None
    if last_reminded is not None:
        return  # already fired

    # Fire notification
    vault_rel = str(path.relative_to(VAULT_ROOT)).replace(".md", "")
    message = body.split("\n")[0] if body else remind_at_str
    fire_notification("Reminder", message, sound, vault_rel)
    logging.info(f"Fired one-shot reminder: {path.name}")

    # Mark as fired
    fields["last_reminded_at"] = now.strftime(DATETIME_FMT)
    write_frontmatter(path, fields, body)


if __name__ == "__main__":
    logging.info("check-reminders started")
    now = datetime.now()

    md_files = [
        p for p in VAULT_ROOT.rglob("*.md")
        if ".obsidian" not in p.parts
    ]

    logging.info(f"Scanning {len(md_files)} files")

    for path in md_files:
        try:
            process_file(path, now)
        except Exception as e:
            logging.error(f"Error processing {path.name}: {e}")
