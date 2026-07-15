"""Operator media ingestion for the PetTripFinder pilot (AES-WEB-002M.2).

The I/O half of the media path, deliberately separated from the pure
``listing_dataset_builder`` (which stays filesystem/CAS-free -- resolved
``ListingAssetRef`` tuples enter it as plain data, the exact
``enrichment_by_key`` overlay precedent):

    operator local file (ingestion-only input; the path never survives
    into any artifact)
      -> read bytes
      -> validate magic signature against the declared/derived MIME
         (extension alone is never trusted)
      -> extract intrinsic pixel dimensions (stdlib header parse -- no
         decode, no Pillow, no decompression-bomb surface)
      -> ArtifactStoreRepository.put_bytes (content-addressed)
      -> ListingAssetRef(role=HERO_IMAGE, asset_hash, alt_text, width,
         height, mime_type, source_kind="OPERATOR_UPLOAD",
         bundle_allowed=True)

V1 operator-ingestion formats: **PNG and JPEG only** (mission §11 -- the
only formats whose dimensions a small deterministic stdlib parse can
honestly extract). SVG/WebP remain bundle-*capable* from M.1's closed MIME
map, but operator ingestion rejects them fail-closed here: SVG because its
script-bearing security posture is unresolved by current authority (§12
"fail closed"), WebP because we do not claim dimensions we cannot honestly
parse in V1.

Determinism: same file bytes -> same hash, same dimensions, same ref. No
clock, no randomness, no network. Malformed or mismatched input raises
:class:`MediaIngestionError` -- never a silently-guessed dimension or MIME.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

from engines.website_generation.contracts.artifacts import ListingAssetRef
from engines.website_generation.contracts.enums import AssetRole

# Formats operator ingestion accepts in V1 (see module docstring for why
# this is narrower than assembly_builders.MEDIA_MIME_EXTENSIONS).
INGESTIBLE_MIME_TYPES = ("image/jpeg", "image/png")

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SOI = b"\xff\xd8"

# JPEG start-of-frame markers that carry dimensions (every SOFn except the
# non-frame DHT/JPG/DAC markers C4/C8/CC).
_JPEG_SOF_MARKERS = frozenset(
    range(0xC0, 0xD0)
) - {0xC4, 0xC8, 0xCC}


class MediaIngestionError(ValueError):
    """Deterministic ingestion rejection: unsupported format, malformed
    image data, or a signature/MIME mismatch. Carries a stable ``reason``
    slug plus a human-readable message."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class IngestedImage:
    """One validated, dimension-parsed operator image, pre-CAS."""

    data: bytes
    mime_type: str
    width: int
    height: int


def _parse_png_dimensions(data: bytes) -> Tuple[int, int]:
    """PNG intrinsic dimensions from the IHDR chunk (bytes 16-24 -- the
    first chunk is IHDR by spec, and its width/height are big-endian
    uint32s). Header-only: no IDAT decode, no zlib."""
    if len(data) < 24 or not data.startswith(_PNG_SIGNATURE):
        raise MediaIngestionError("malformed_png", "not a valid PNG signature")
    if data[12:16] != b"IHDR":
        raise MediaIngestionError("malformed_png", "PNG missing leading IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise MediaIngestionError("malformed_png", "PNG declares non-positive dimensions")
    return width, height


def _parse_jpeg_dimensions(data: bytes) -> Tuple[int, int]:
    """JPEG intrinsic dimensions from the first SOFn frame header: walk the
    marker segments (each ``FF xx`` + big-endian length) until a
    start-of-frame marker, whose payload carries height (offset +3) and
    width (offset +5) as big-endian uint16s. Entropy-coded data is never
    decoded -- the walk stops at the first frame header."""
    if len(data) < 4 or not data.startswith(_JPEG_SOI):
        raise MediaIngestionError("malformed_jpeg", "not a valid JPEG SOI signature")
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            raise MediaIngestionError("malformed_jpeg", "JPEG marker desync at offset %d" % offset)
        marker = data[offset + 1]
        if marker == 0xD8 or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            offset += 2  # standalone markers carry no length
            continue
        if marker == 0xD9:  # EOI before any frame header
            break
        segment_length = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
        if segment_length < 2:
            raise MediaIngestionError("malformed_jpeg", "JPEG segment length < 2")
        if marker in _JPEG_SOF_MARKERS:
            if offset + 9 > len(data):
                raise MediaIngestionError("malformed_jpeg", "JPEG SOF segment truncated")
            height = struct.unpack(">H", data[offset + 5 : offset + 7])[0]
            width = struct.unpack(">H", data[offset + 7 : offset + 9])[0]
            if width <= 0 or height <= 0:
                raise MediaIngestionError(
                    "malformed_jpeg", "JPEG declares non-positive dimensions"
                )
            return width, height
        offset += 2 + segment_length
    raise MediaIngestionError("malformed_jpeg", "no JPEG frame header found")


def validate_image_bytes(data: bytes) -> IngestedImage:
    """Sniff, validate, and dimension-parse operator image bytes.

    The MIME type is derived from the *bytes* (magic signature), never
    from a filename extension -- an extension/signature mismatch therefore
    cannot exist at this layer (the signature is the truth). Unsupported
    or malformed data raises :class:`MediaIngestionError` (fail-closed,
    mission §12)."""
    if data.startswith(_PNG_SIGNATURE):
        width, height = _parse_png_dimensions(data)
        return IngestedImage(data=data, mime_type="image/png", width=width, height=height)
    if data.startswith(_JPEG_SOI):
        width, height = _parse_jpeg_dimensions(data)
        return IngestedImage(data=data, mime_type="image/jpeg", width=width, height=height)
    raise MediaIngestionError(
        "unsupported_format",
        "not a supported operator-ingestible image (PNG/JPEG only in V1)",
    )


def ingest_operator_image(
    source: Union[str, Path],
    cas,
    *,
    alt_text: str = "",
) -> ListingAssetRef:
    """Ingest one operator-supplied local image file into the CAS and
    return the durable ``ListingAssetRef`` the (pure) dataset builder
    consumes. The local path is ingestion-only input -- nothing derived
    from it (name, directory, extension) survives into the returned ref.

    ``cas`` is any object with ``put_bytes(data) -> sha256`` --
    ``ArtifactStoreRepository`` in production, a stub in tests (the same
    duck-typed injection the SiteBundleRepository asset_bytes mapping
    uses)."""
    path = Path(source)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise MediaIngestionError(
            "unreadable_file", "cannot read operator image %r: %s" % (str(path), exc)
        ) from exc
    validated = validate_image_bytes(data)
    asset_hash = cas.put_bytes(validated.data)
    return ListingAssetRef(
        role=AssetRole.HERO_IMAGE,
        asset_hash=asset_hash,
        alt_text=alt_text,
        width=validated.width,
        height=validated.height,
        mime_type=validated.mime_type,
        source_kind="OPERATOR_UPLOAD",
        bundle_allowed=True,
        attribution_text="",
    )
