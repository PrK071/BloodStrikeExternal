# Python | ExternalCore/ntll_memory.py | Python 3.12+ x64 / Windows
# ntdll-direct process memory reader. Uses NtOpenProcess / NtReadVirtualMemory /
# NtWriteVirtualMemory from ntdll instead of the kernel32 wrappers, so it skips
# kernel32 API hooks (the most common user-mode anticheat hook).
import ctypes
from ctypes import wintypes
import os
import threading

from .memory import MemoryReadError, check_range

from .win32_memory import find_module, ProcessModule  # noqa: F401

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000


class _CLIENT_ID(ctypes.Structure):
    _fields_ = [("UniqueProcess", wintypes.HANDLE),
                ("UniqueThread", wintypes.HANDLE)]


class _OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Length", wintypes.ULONG),
                ("RootDirectory", wintypes.HANDLE),
                ("ObjectName", ctypes.c_void_p),
                ("Attributes", wintypes.ULONG),
                ("SecurityDescriptor", ctypes.c_void_p),
                ("SecurityQualityOfService", ctypes.c_void_p)]


def _ntdll():
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    ntdll.NtOpenProcess.restype = ctypes.c_long
    ntdll.NtOpenProcess.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
                                    ctypes.POINTER(_OBJECT_ATTRIBUTES), ctypes.POINTER(_CLIENT_ID)]
    ntdll.NtReadVirtualMemory.restype = ctypes.c_long
    ntdll.NtReadVirtualMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ntdll.NtWriteVirtualMemory.restype = ctypes.c_long
    ntdll.NtWriteVirtualMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ntdll.NtClose.restype = ctypes.c_long
    ntdll.NtClose.argtypes = [wintypes.HANDLE]
    return ntdll


class NtProcessMemory:
    """Own a handle opened via NtOpenProcess; read/write via ntdll directly."""

    def __init__(self, pid: int):
        if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
            raise ValueError("pid must be a positive DWORD")
        self.pid = pid
        self._ntdll = _ntdll()
        self._lock = threading.RLock()
        self.dictionary_key_hashes = {}

        cid = _CLIENT_ID(pid, 0)
        oa = _OBJECT_ATTRIBUTES(ctypes.sizeof(_OBJECT_ATTRIBUTES), 0, None, 0, None, None)
        self._handle = wintypes.HANDLE()
        st = self._ntdll.NtOpenProcess(
            ctypes.byref(self._handle),
            PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_LIMITED_INFORMATION,
            ctypes.byref(oa), ctypes.byref(cid))
        if st != 0 or not self._handle:
            raise ctypes.WinError(ctypes.get_last_error() or st)

    def _open_handle(self):
        if not self._handle:
            raise MemoryReadError("process reader is closed")
        return self._handle

    @property
    def image_path(self) -> str:
        with self._lock:
            api = ctypes.WinDLL("kernel32", use_last_error=True)
            api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                       wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
            api.QueryFullProcessImageNameW.restype = wintypes.BOOL
            length = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(length.value)
            if not api.QueryFullProcessImageNameW(self._open_handle(), 0, buffer, ctypes.byref(length)):
                raise ctypes.WinError(ctypes.get_last_error())
            return buffer.value

    def read(self, address: int, size: int) -> bytes:
        check_range(address, size)
        with self._lock:
            if not size:
                return b""
            buffer = (ctypes.c_ubyte * size)()
            count = ctypes.c_size_t(0)
            st = self._ntdll.NtReadVirtualMemory(self._open_handle(), address, buffer, size,
                                                 ctypes.byref(count))
            if st != 0 or count.value != size:
                raise MemoryReadError(st or 299,
                                      f"NtReadVirtualMemory failed at {address:#x}: "
                                      f"{count.value}/{size} bytes (NTSTATUS {st:#x})")
            return bytes(buffer)

    def write(self, address: int, data: bytes) -> None:
        data = bytes(data)
        check_range(address, len(data))
        with self._lock:
            if not data:
                return
            buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
            count = ctypes.c_size_t(0)
            st = self._ntdll.NtWriteVirtualMemory(self._open_handle(), address, buf, len(data),
                                                  ctypes.byref(count))
            if st != 0 or count.value != len(data):
                raise MemoryReadError(st or 299,
                                      f"NtWriteVirtualMemory failed at {address:#x} (NTSTATUS {st:#x})")

    def close(self):
        with self._lock:
            if self._handle:
                handle, self._handle = self._handle, None
                self._ntdll.NtClose(handle)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
