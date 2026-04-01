from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Mp4AtomProbeResult:
    path: Path
    size_bytes: int
    header_has_ftyp: bool
    header_has_moov: bool
    header_has_mdat: bool
    file_has_moov: bool


def _contains_needle(path: Path, needle: bytes, *, chunk_size: int = 8 * 1024 * 1024) -> bool:
    if chunk_size < 1024 * 1024:
        chunk_size = 1024 * 1024

    overlap = max(0, len(needle) - 1)
    prev = b""
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                return False
            data = prev + b
            if data.find(needle) != -1:
                return True
            prev = data[-overlap:] if overlap else b""


def probe_mp4_atoms(path: str | Path, *, header_bytes: int = 64 * 1024) -> Mp4AtomProbeResult:
    p = Path(path)
    size = p.stat().st_size
    head = p.read_bytes()[:header_bytes]

    header_has_ftyp = b"ftyp" in head
    header_has_moov = b"moov" in head
    header_has_mdat = b"mdat" in head

    file_has_moov = _contains_needle(p, b"moov")

    return Mp4AtomProbeResult(
        path=p,
        size_bytes=size,
        header_has_ftyp=header_has_ftyp,
        header_has_moov=header_has_moov,
        header_has_mdat=header_has_mdat,
        file_has_moov=file_has_moov,
    )

