import subprocess

from . import icons
from .config import NOTIFIER, VAULT_NAME


def fire(subtitle: str, message: str, sound: str, vault_relative_path: str | None = None, color: str | None = None) -> None:
    """Fire a terminal-notifier notification.

    Args:
        subtitle:            Shown below the 'mindspace' title.
        message:             The notification body text.
        sound:               Sound name, or 'none' to suppress.
        vault_relative_path: Path relative to vault root (without .md extension).
                             If provided, clicking the notification opens the note in Obsidian.
        color:               HTML color name for the content image (e.g. 'steelblue', 'coral').
                             If invalid or omitted, no image is shown.
    """
    args = [
        NOTIFIER,
        "-title", "mindspace",
        "-subtitle", subtitle,
        "-message", message,
    ]
    if sound and sound.lower() != "none":
        args += ["-sound", sound]
    if vault_relative_path:
        encoded = vault_relative_path.replace(" ", "%20")
        args += ["-open", f"obsidian://open?vault={VAULT_NAME}&file={encoded}"]

    icon_path = icons.generate(color) if color else None
    if icon_path:
        args += ["-contentImage", str(icon_path)]

    subprocess.run(args)

    if icon_path:
        icon_path.unlink(missing_ok=True)
