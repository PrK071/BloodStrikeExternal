# Python | ExternalCore/win32_memory.py | Python 3.12+ x64 / Windows | read-only process adapter.
"""Documented Win32 reads; no injection, privilege change, driver or write API.

API contract: https://learn.microsoft.com/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory
Importing this file does not select or open any process.
"""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import threading

from .memory import MemoryReadError, check_range

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _kernel32():
    if os.name != "nt" or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise OSError("a 64-bit Python interpreter on Windows is required")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    api.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                      ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    api.ReadProcessMemory.restype = wintypes.BOOL
    api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                              ctypes.POINTER(wintypes.DWORD)]
    api.QueryFullProcessImageNameW.restype = wintypes.BOOL
    return api


class WindowsProcessMemory:
    """Own a query/read handle. Failed or partial reads return no decoded bytes."""
    page_size = 4096

    def __init__(self, pid: int):
        if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
            raise ValueError("pid must be a positive DWORD")
        self._api = _kernel32()
        self._lock = threading.RLock()
        self._handle = self._api.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not self._handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.pid = pid
        # String hashes only: never retain frame values, object identities or pages.
        self.dictionary_key_hashes = {}

    def _open_handle(self):
        if not self._handle:
            raise MemoryReadError("process reader is closed")
        return self._handle

    @property
    def image_path(self) -> str:
        with self._lock:
            length = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(length.value)
            if not self._api.QueryFullProcessImageNameW(self._open_handle(), 0, buffer, ctypes.byref(length)):
                raise ctypes.WinError(ctypes.get_last_error())
            return buffer.value

    def read(self, address: int, size: int) -> bytes:
        check_range(address, size)
        # WinDLL releases the GIL. Keep ownership stable until the API returns.
        with self._lock:
            handle = self._open_handle()
            if not size:
                return b""
            buffer = (ctypes.c_ubyte * size)()
            count = ctypes.c_size_t()
            ok = self._api.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(count))
            if not ok or count.value != size:
                error = ctypes.get_last_error() if not ok else 299
                raise MemoryReadError(error, f"ReadProcessMemory failed/partial at {address:#x}: "
                                             f"{count.value}/{size} bytes (Win32 {error})")
            return bytes(buffer)

    def close(self):
        with self._lock:
            if self._handle:
                handle, self._handle = self._handle, None
                if not self._api.CloseHandle(handle):
                    raise ctypes.WinError(ctypes.get_last_error())

    def __enter__(self):
        with self._lock:
            self._open_handle()
        return self

    def __exit__(self, *args):
        self.close()


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
                ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260)]


@dataclass(frozen=True, slots=True)
class ProcessModule:
    base: int
    size: int
    path: str


def find_module(pid: int, expected_path: str) -> ProcessModule:
    """Select by full path, never by a guessed/preferred module base."""
    api = _kernel32()
    api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    api.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    api.Module32FirstW.restype = wintypes.BOOL
    api.Module32NextW.argtypes = api.Module32FirstW.argtypes
    api.Module32NextW.restype = wintypes.BOOL
    snapshot = api.CreateToolhelp32Snapshot(0x8 | 0x10, pid)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    matches = []
    wanted = os.path.normcase(os.path.realpath(expected_path))
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = api.Module32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if os.path.normcase(os.path.realpath(entry.szExePath)) == wanted:
                matches.append(ProcessModule(entry.modBaseAddr, entry.modBaseSize, entry.szExePath))
            ok = api.Module32NextW(snapshot, ctypes.byref(entry))
        error = ctypes.get_last_error()
        if error != 18:  # ERROR_NO_MORE_FILES is the only normal terminator.
            raise ctypes.WinError(error)
    finally:
        api.CloseHandle(snapshot)
    if len(matches) != 1:
        raise MemoryReadError(f"expected one module with the verified full path, found {len(matches)}")
    return matches[0]
