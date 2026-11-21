# Python | ExternalCore/syscall_memory.py | Python 3.12+ x64 / Windows
# Direct-syscall process memory reader. The heavy lifting is in syscall.dll
# (raw `syscall` instructions for NtOpenProcess/NtReadVirtualMemory/
# NtWriteVirtualMemory), which bypasses both kernel32 AND ntdll hooks.
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

_DLL_CANDIDATES = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "syscall.dll"),
    r"C:\Users\luiz\km_cheat\syscall\syscall.dll",
)


def _load_dll():
    for path in _DLL_CANDIDATES:
        if os.path.exists(path):
            dll = ctypes.WinDLL(path, use_last_error=True)
            dll.sc_open_process.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
            dll.sc_open_process.restype = wintypes.HANDLE
            dll.sc_read.argtypes = [wintypes.HANDLE, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_ulong]
            dll.sc_read.restype = ctypes.c_long
            dll.sc_write.argtypes = [wintypes.HANDLE, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_ulong]
            dll.sc_write.restype = ctypes.c_long
            dll.sc_close.argtypes = [wintypes.HANDLE]
            dll.sc_close.restype = wintypes.BOOL
            return dll
    raise OSError("syscall.dll not found; build it with km_cheat/syscall/build.bat")


class SyscallProcessMemory:
    """Own a handle opened via a raw NtOpenProcess syscall; read/write via
    raw NtReadVirtualMemory/NtWriteVirtualMemory syscalls."""

    def __init__(self, pid: int):
        if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
            raise ValueError("pid must be a positive DWORD")
        self.pid = pid
        self._lock = threading.RLock()
        self._dll = _load_dll()
        self.dictionary_key_hashes = {}

        self._handle = self._dll.sc_open_process(
            PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_LIMITED_INFORMATION,
            pid)
        if not self._handle:
            raise ctypes.WinError(ctypes.get_last_error())

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
            st = self._dll.sc_read(self._open_handle(), address, buffer, size)
            if st != 0:
                raise MemoryReadError(st, f"syscall read failed at {address:#x} (NTSTATUS {st:#x})")
            return bytes(buffer)

    def write(self, address: int, data: bytes) -> None:
        data = bytes(data)
        check_range(address, len(data))
        with self._lock:
            if not data:
                return
            buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
            st = self._dll.sc_write(self._open_handle(), address, buf, len(data))
            if st != 0:
                raise MemoryReadError(st, f"syscall write failed at {address:#x} (NTSTATUS {st:#x})")

    def close(self):
        with self._lock:
            if self._handle:
                handle, self._handle = self._handle, None
                self._dll.sc_close(handle)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
