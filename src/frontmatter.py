import re
from datetime import datetime
from pathlib import Path

from .config import DATETIME_FMT

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)
FIELD_RE       = re.compile(r"^(?P<key>\w+):\s*(?P<value>.+)$", re.MULTILINE)


def parse(text: str) -> tuple[dict, str]:
    """Return (fields dict, body text). Both empty if no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields = {k: v.strip() for k, v in FIELD_RE.findall(m.group(1))}
    return fields, m.group(2).strip()


def write(path: Path, fields: dict, body: str) -> None:
    """Write updated frontmatter + body back to the file."""
    lines = "\n".join(f"{k}: {v}" for k, v in fields.items())
    path.write_text(f"---\n{lines}\n---\n{body}\n", encoding="utf-8")


def parse_dt(value: str | None) -> datetime | None:
    """Parse a datetime string. Returns None if value is None or unparseable."""
    if value is None:
        return None
    try:
        return datetime.strptime(value.strip(), DATETIME_FMT)
    except ValueError:
        return None
