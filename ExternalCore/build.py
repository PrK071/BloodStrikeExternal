# Python | ExternalCore/build.py | Python 3.12+ | identity gate for the audited PE.
"""Only disk identity is established here; a live process image is a separate claim."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct

from .entity_position import SAMPLE_SHA256


class BuildMismatchError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ModuleIdentity:
    base: int
    size: int
    sha256: str

    def __post_init__(self):
        if type(self.base) is not int or self.base <= 0 or self.base % 0x1000:
            raise ValueError("module base must be a positive page-aligned integer")
        if type(self.size) is not int or self.size <= 0 or self.base + self.size > 1 << 64:
            raise ValueError("invalid module size")
        if self.sha256 != SAMPLE_SHA256:
            raise BuildMismatchError("unsupported sample SHA-256; offsets were not demonstrated for this build")

    def address(self, rva: int, size: int = 1) -> int:
        if type(rva) is not int or type(size) is not int or rva < 0 or size < 1 or rva + size > self.size:
            raise ValueError("RVA is outside the module")
        return self.base + rva


def verify_sample(path: str | Path) -> dict:
    """Hash the original file before selecting any process or applying a layout."""
    path = Path(path).resolve(strict=True)
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != SAMPLE_SHA256:
            raise BuildMismatchError(f"unsupported sample SHA-256: {digest}")
        source.seek(0)
        dos = source.read(64)
        if dos[:2] != b"MZ":
            raise BuildMismatchError("invalid DOS signature")
        source.seek(struct.unpack_from("<I", dos, 0x3C)[0])
        headers = source.read(24 + 64)
    if headers[:4] != b"PE\0\0" or struct.unpack_from("<H", headers, 4)[0] != 0x8664:
        raise BuildMismatchError("sample is not an AMD64 PE")
    if struct.unpack_from("<H", headers, 24)[0] != 0x20B:
        raise BuildMismatchError("sample is not PE32+")
    return {"path": str(path), "sha256": digest,
            "image_size": struct.unpack_from("<I", headers, 24 + 56)[0]}
