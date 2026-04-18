# mindspace-automation

A lightweight macOS reminder system that lives in your Obsidian vault.

Write reminders as markdown frontmatter anywhere in your vault. A launchd agent scans your notes periodically and fires native macOS notifications with sound and a click-to-open Obsidian deep link.

## How it works

- Reminders are plain `.md` files with YAML frontmatter - no app, no database
- A Python script runs every 5 minutes via launchd
- Notifications are delivered via `terminal-notifier` with optional color icons and sounds

## Reminder format

**One-shot:**
```yaml
---
remind_at: 2026-04-19 09:00
sound: Blow
color: steelblue
---
Call dentist to reschedule
```

**Recurring:**
```yaml
---
recur: every friday at 09:00
sound: Submarine
color: steelblue
---
Book working hours into PMS
```

Both can live anywhere in your vault. The script writes `last_reminded_at` and `remind_at` (next occurrence) back into the file after firing.

`color` accepts any HTML color name. `sound` accepts any macOS system sound (Basso, Blow, Bottle, Frog, Glass, Hero, Morse, Ping, Pop, Purr, Sosumi, Submarine, Tink). Both default to `purple` / `Submarine` if omitted. Use `sound: none` to suppress sound.

## Requirements

- macOS
- [Obsidian](https://obsidian.md)
- `brew install terminal-notifier uv`

## Setup

```bash
git clone https://github.com/schoenfr/mindspace-automation
cd mindspace-automation
uv sync
```

Edit `config.py` to point to your vault:

```python
VAULT_ROOT = Path.home() / "your" / "vault" / "path"
VAULT_NAME = "your-vault-name"
```

Set up the launchd agent:

```bash
# edit the paths in config/com.mindspace.reminders.plist to match your setup
ln -sf /path/to/mindspace/config/com.mindspace.reminders.plist \
       ~/Library/LaunchAgents/com.mindspace.reminders.plist
launchctl load ~/Library/LaunchAgents/com.mindspace.reminders.plist
```

In **System Settings → Notifications → Terminal Notifier**: set style to **Alerts**.
Add Terminal Notifier to your Focus mode allowed apps.
