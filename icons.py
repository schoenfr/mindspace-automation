import logging
import struct
import tempfile
import zlib
from pathlib import Path

import webcolors


def _make_png(r: int, g: int, b: int, size: int = 64) -> bytes:
    """Generate a solid-color PNG as bytes."""
    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    raw  = b"".join(b"\x00" + bytes([r, g, b] * size) for _ in range(size))
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


def generate(color_name: str) -> Path | None:
    """Generate a 64x64 PNG for a named HTML color.

    Returns the path to a temporary file, or None if the color name is invalid.
    The caller is responsible for deleting the file after use.
    """
    try:
        rgb = webcolors.name_to_hex(color_name)
        r, g, b = webcolors.hex_to_rgb(rgb)
    except (ValueError, AttributeError):
        logging.warning(f"Unknown color name: {color_name!r} - notification will have no icon")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(_make_png(r, g, b))
    tmp.close()
    return Path(tmp.name)
