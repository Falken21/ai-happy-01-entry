#!/usr/bin/env python3
"""Entrypoint for the make.fun ai-happy-01 entry "Sunny Meadow Cat".

The entry ships one fixed picture, entry.png, sitting next to this file:
a chubby orange cat smiling in a sunny flower meadow, under a smiling
sun, a rainbow, clouds, birds, butterflies and a hot-air balloon.

Running the program publishes that picture to the grader's output
directory as entry.png. Before anything is written, the picture passes
through a small validation gate that mirrors the competition rules:

* the bytes must be a genuine PNG or JPEG image -- magic bytes plus a
  real header parse, never just a filename extension check,
* the file must weigh at most 1 MiB,
* the picture must be at most 1024 x 1024 pixels.

Only a picture that clears the gate is copied, byte for byte, to
$MAKEFUN_OUTPUT_DIR/entry.png. The variable defaults to /output, which
is where the grader looks; outside the grading container it can point
anywhere:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py

The program is deterministic by construction: same input picture, same
output bytes, no clock, no randomness, no network access, and nothing
outside the Python standard library.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PICTURE_PATH = os.path.join(HERE, "entry.png")
OUTPUT_NAME = "entry.png"

LIMIT_BYTES = 1024 * 1024  # 1 MiB
LIMIT_WIDTH = 1024
LIMIT_HEIGHT = 1024

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8"  # start-of-image marker

# JPEG start-of-frame markers. An SOF segment stores the picture's
# height and width, which is exactly what the gate needs.
SOF_MARKERS = frozenset(
    (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)
)
# Markers that stand alone with no length field: TEM, SOI, EOI, RST0-7.
STANDALONE_MARKERS = frozenset((0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)))


class PictureError(ValueError):
    """Raised when the shipped picture fails the validation gate."""


def png_dimensions(blob):
    """Extract (width, height) from a PNG blob's IHDR chunk."""
    # Layout: 8-byte signature, then chunk length (4), type (4), data.
    # The first chunk of a valid PNG is always IHDR, whose data starts
    # with width and height as big-endian unsigned 32-bit integers.
    if len(blob) < 8 + 4 + 4 + 8:
        raise PictureError("PNG file is truncated before its IHDR data")
    if blob[12:16] != b"IHDR":
        raise PictureError("PNG file does not start with an IHDR chunk")
    width, height = struct.unpack_from(">II", blob, 16)
    return width, height


def jpeg_dimensions(blob):
    """Walk JPEG segments; return (width, height) from the first SOF."""
    pos = 2  # the caller already matched the SOI marker at bytes 0-1
    end = len(blob)
    while pos + 1 < end:
        if blob[pos] != 0xFF:
            raise PictureError("JPEG stream lost marker alignment")
        marker = blob[pos + 1]
        if marker == 0xFF:
            pos += 1  # padding byte in front of a marker; step over it
            continue
        if marker in SOF_MARKERS:
            if pos + 9 > end:
                raise PictureError("JPEG start-of-frame segment truncated")
            height, width = struct.unpack_from(">HH", blob, pos + 5)
            return width, height
        if marker in STANDALONE_MARKERS:
            pos += 2
            continue
        if pos + 4 > end:
            raise PictureError("JPEG segment header is truncated")
        (segment_length,) = struct.unpack_from(">H", blob, pos + 2)
        if segment_length < 2:
            raise PictureError("JPEG segment declares an invalid length")
        pos += 2 + segment_length
    raise PictureError("JPEG stream has no start-of-frame segment")


def identify_dimensions(blob):
    """Return (format_name, width, height) for a PNG or JPEG blob."""
    if blob[:8] == PNG_MAGIC:
        width, height = png_dimensions(blob)
        return "PNG", width, height
    if blob[:2] == JPEG_MAGIC:
        width, height = jpeg_dimensions(blob)
        # A complete JPEG stream ends with the end-of-image marker; a
        # stream without it is truncated, however healthy its SOF looks.
        if not blob.endswith(b"\xff\xd9"):
            raise PictureError("JPEG stream misses its end-of-image marker")
        return "JPEG", width, height
    raise PictureError("picture is neither PNG nor JPEG (bad magic bytes)")


def load_and_check(path):
    """Read the picture at *path*, enforce the gate, return its bytes."""
    with open(path, "rb") as handle:
        blob = handle.read()
    if len(blob) > LIMIT_BYTES:
        raise PictureError(
            "picture weighs %d bytes, over the 1 MiB limit" % len(blob)
        )
    fmt, width, height = identify_dimensions(blob)
    if width == 0 or height == 0:
        raise PictureError("%s picture declares a zero dimension" % fmt)
    if width > LIMIT_WIDTH or height > LIMIT_HEIGHT:
        raise PictureError(
            "%s picture is %dx%d, over the 1024x1024 limit"
            % (fmt, width, height)
        )
    return blob


def publish(blob):
    """Write the picture bytes into the output directory as entry.png."""
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, OUTPUT_NAME)
    with open(target, "wb") as handle:
        handle.write(blob)
    return target


def main():
    blob = load_and_check(PICTURE_PATH)
    publish(blob)
    return 0


if __name__ == "__main__":
    sys.exit(main())
