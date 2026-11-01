# Python | tests/native_fixture.py | Python 3.12+ x64 / Windows | owned child process fixture.
"""Reserve sparse module-shaped memory; no game files/processes are involved."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry_fixture import fixture_segments


def main():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    api.VirtualAlloc.restype = ctypes.c_void_p
    api.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    api.VirtualFree.restype = wintypes.BOOL
    base = api.VirtualAlloc(None, 0x94E9000, 0x2000, 0x01)  # Reserve, PAGE_NOACCESS.
    if not base:
        raise ctypes.WinError(ctypes.get_last_error())
    arena = ctypes.create_string_buffer(0x8000)
    try:
        segments, module, a = fixture_segments(base, ctypes.addressof(arena))
        committed = set()
        for segment in segments:
            if base <= segment.address < base + module.size:
                first = segment.address & ~0xFFF
                last = (segment.address + len(segment.data) - 1) & ~0xFFF
                for page in range(first, last + 1, 0x1000):
                    if page not in committed:
                        if not api.VirtualAlloc(page, 0x1000, 0x1000, 0x04):
                            raise ctypes.WinError(ctypes.get_last_error())
                        committed.add(page)
            ctypes.memmove(segment.address, segment.data, len(segment.data))
        print(json.dumps({"pid": os.getpid(), "base": base, "addresses": a,
                          "provenance": "owned_synthetic_child_not_bloodstrike"}), flush=True)
        for line in sys.stdin:
            command = line.strip()
            if command == "mutate":
                ctypes.c_float.from_address(a["position"]).value = 99.5
                print("mutated", flush=True)
            elif command == "exit":
                break
    finally:
        api.VirtualFree(base, 0, 0x8000)


if __name__ == "__main__":
    main()
