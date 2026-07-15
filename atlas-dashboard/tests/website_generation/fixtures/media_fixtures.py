"""Deterministic synthetic test images (AES-WEB-002M.2).

Tiny, repository-owned, programmatically-generated fixture bytes -- never
downloaded, never random, never copyrighted third-party photography, never
a user-machine path (mission §14). Every builder is a pure function of its
arguments: the same call always yields the same bytes, so content hashes
are stable across machines and runs.

* :func:`make_test_png` -- a *fully valid* minimal PNG (real IHDR/IDAT/IEND
  chunks with correct CRCs; ``zlib.compress`` is deterministic for a fixed
  input at the default level), decodable by any browser.
* :func:`make_test_jpeg` -- a minimal JPEG whose SOI/APP0/SOF0 marker
  stream is structurally valid and dimension-parseable. It carries no
  entropy-coded scan data (parser-level fixture: ingestion validates
  signature + frame header, never decodes pixels -- documented honestly,
  not claimed as a renderable photograph).
"""

from __future__ import annotations

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def make_test_png(width: int = 6, height: int = 4, color: tuple = (120, 140, 90)) -> bytes:
    """A fully valid 8-bit RGB PNG of the given dimensions, one flat color."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(color) * width  # filter byte 0 + RGB pixels
    idat = zlib.compress(row * height)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def make_test_jpeg(width: int = 6, height: int = 4) -> bytes:
    """A minimal, dimension-parseable JPEG marker stream (SOI + JFIF APP0 +
    single-component SOF0 + EOI). See module docstring for scope."""
    soi = b"\xff\xd8"
    app0 = (
        b"\xff\xe0"
        + struct.pack(">H", 16)
        + b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"
    )
    sof0 = (
        b"\xff\xc0"
        + struct.pack(">H", 11)  # 8 + 3 * 1 component
        + b"\x08"                # 8-bit precision
        + struct.pack(">HH", height, width)
        + b"\x01\x11\x00"        # 1 component, 1x1 sampling, quant table 0
    )
    eoi = b"\xff\xd9"
    return soi + app0 + sof0 + eoi
