from pathlib import Path

VAULT_ROOT    = Path.home() / "mindspace" / "obsidian"
VAULT_NAME    = "obsidian"  # must match vault folder name as Obsidian sees it
OVERVIEW_FILE = VAULT_ROOT / "Overview" / "Reminders.md"
LOG_FILE      = Path.home() / "mindspace" / "logs" / "reminders.log"
NOTIFIER      = "/opt/homebrew/bin/terminal-notifier"
DATETIME_FMT  = "%Y-%m-%d %H:%M"
DEFAULT_SOUND = "Submarine"
DEFAULT_COLOR = "purple"
