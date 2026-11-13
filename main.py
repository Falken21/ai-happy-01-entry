#!/usr/bin/env python3
"""Entry for make.fun ai-happy-01 ("Sunny Meadow Cat").

Writes one cheerful picture, entry.png, to the output directory: a fat
orange cat smiling in a sunny flower meadow, under a smiling sun, a
rainbow, clouds, butterflies and a hot-air balloon.

Deterministic by design: the same fixed picture on every run, no
randomness, no network, standard library only. Before copying, the
picture is validated against the competition's image gate: a real PNG
or JPEG signature, at most 1 MiB, and at most 1024x1024 pixels.

Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import shutil
import struct

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1 * 1024 * 1024  # 1 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024


def read_png_dimensions(data: bytes) -> tuple:
    """Return (width, height) from a PNG's IHDR chunk."""
    if len(data) < 33 or data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file (bad signature)")
    if data[12:16] != b"IHDR":
        raise ValueError("not a PNG file (missing IHDR chunk)")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


JPEG_SIGNATURE = b"\xff\xd8\xff"
# Start-of-frame markers that carry the picture's dimensions.
JPEG_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def read_jpeg_dimensions(data: bytes) -> tuple:
    """Return (width, height) from a JPEG's start-of-frame segment."""
    if len(data) < 4 or data[:3] != JPEG_SIGNATURE:
        raise ValueError("not a JPEG file (bad signature)")
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError("not a JPEG file (lost marker sync)")
        marker = data[pos + 1]
        if marker in JPEG_SOF_MARKERS:
            if pos + 9 > len(data):
                raise ValueError("truncated JPEG (short SOF segment)")
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2  # stand-alone markers carry no length field
            continue
        segment_length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if segment_length < 2:
            raise ValueError("not a JPEG file (bad segment length)")
        pos += 2 + segment_length
    raise ValueError("not a JPEG file (no start-of-frame segment)")


def validate_picture(path: str) -> None:
    """Check the picture against the image gate before it is copied."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > MAX_BYTES:
        raise ValueError("picture is larger than 1 MiB: %d bytes" % len(data))
    if data[:8] == PNG_SIGNATURE:
        width, height = read_png_dimensions(data)
    elif data[:3] == JPEG_SIGNATURE:
        width, height = read_jpeg_dimensions(data)
    else:
        raise ValueError("not a PNG or JPEG file (bad signature)")
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        raise ValueError(
            "picture is larger than 1024x1024: %dx%d" % (width, height)
        )


def main() -> None:
    validate_picture(SOURCE)
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)
    entry_path = os.path.join(output_dir, "entry.png")
    shutil.copyfile(SOURCE, entry_path)


if __name__ == "__main__":
    main()
