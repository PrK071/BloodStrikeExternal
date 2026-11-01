# Python | ExternalCore/memory.py | Python 3.12+ | exact, bounded address-space reads.
"""Address-space contract shared by recorded data and the Windows reader."""
from bisect import bisect_right
from dataclasses import dataclass
from typing import Protocol

MAX_ADDRESS = (1 << 64) - 1
MAX_READ = 16 * 1024 * 1024


class MemoryReadError(OSError):
    """No complete read is available; partial bytes must never be decoded."""


def check_range(address: int, size: int) -> None:
    if type(address) is not int or type(size) is not int:
        raise TypeError("address and size must be integers")
    if address < 0 or size < 0 or size > MAX_READ or address > MAX_ADDRESS:
        raise ValueError("invalid or excessive memory range")
    if size and address > MAX_ADDRESS - size + 1:
        raise ValueError("memory range overflows uint64")


class MemoryReader(Protocol):
    def read(self, address: int, size: int) -> bytes: ...


class PageSnapshotReader:
    """One-pass page cache; instantiate again for every independent observation.

    Only readers explicitly advertising full-page support use this adapter.
    No cache is shared between frames or metadata passes. This reduces small
    Win32 reads; it does not acquire a target lock or guarantee atomic pages.
    """
    def __init__(self, reader, *, max_pages=2048):
        if type(max_pages) is not int or not 1 <= max_pages <= 4096:
            raise ValueError("invalid page-cache budget")
        self.reader,self.max_pages,self.pages,self.unavailable = reader,max_pages,{},set()

    def read(self,address,size):
        check_range(address,size)
        result=bytearray()
        while len(result)<size:
            cursor=address+len(result)
            page=cursor & ~4095
            amount=min(size-len(result),4096-(cursor-page))
            if page not in self.pages and page not in self.unavailable and len(self.pages)<self.max_pages:
                try:self.pages[page]=read_exact(self.reader,page,4096)
                except MemoryReadError:self.unavailable.add(page)
            if page in self.pages:
                result.extend(self.pages[page][cursor-page:cursor-page+amount])
            else:
                result.extend(read_exact(self.reader,cursor,amount))
        return bytes(result)


def read_exact(reader: MemoryReader, address: int, size: int) -> bytes:
    check_range(address, size)
    data = reader.read(address, size)
    if not isinstance(data, bytes) or len(data) != size:
        raise MemoryReadError(f"short/non-byte read at {address:#x}: expected {size} bytes")
    return data


@dataclass(frozen=True, slots=True)
class Segment:
    address: int
    data: bytes


class SnapshotMemory:
    """Immutable, sparse address space; adjacent segments may satisfy one read."""

    def __init__(self, segments):
        copied = []
        for item in segments:
            if not isinstance(item.data, (bytes, bytearray, memoryview)):
                raise TypeError("segment data must be bytes-like")
            data = bytes(item.data)
            check_range(item.address, len(data))
            if data:
                copied.append(Segment(item.address, data))
        self.segments = tuple(sorted(copied, key=lambda s: s.address))
        for left, right in zip(self.segments, self.segments[1:]):
            if left.address + len(left.data) > right.address:
                raise ValueError("overlapping memory segments")
        self._starts = tuple(s.address for s in self.segments)

    def read(self, address: int, size: int) -> bytes:
        check_range(address, size)
        if size == 0:
            return b""
        index = bisect_right(self._starts, address) - 1
        result = bytearray()
        cursor = address
        while len(result) < size:
            if index < 0 or index >= len(self.segments):
                raise MemoryReadError(f"unmapped range at {cursor:#x}")
            segment = self.segments[index]
            offset = cursor - segment.address
            if offset < 0 or offset >= len(segment.data):
                raise MemoryReadError(f"unmapped range at {cursor:#x}")
            amount = min(size - len(result), len(segment.data) - offset)
            result.extend(segment.data[offset:offset + amount])
            cursor += amount
            index += 1
        return bytes(result)
