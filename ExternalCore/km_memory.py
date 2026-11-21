# Python | ExternalCore/km_memory.py | Python 3.12+ x64 / Windows
# Kernel read/write through the manually-mapped km_rw driver.
#
# The driver is loaded by kdmapper (not the SCM), so there is no device and no
# IOCTL. Communication happens through a named shared section
# (\BaseNamedObjects\KmRwShared) that the driver created and a worker thread
# polls. Same public interface as win32_memory.WindowsProcessMemory:
#
#   with KernelProcessMemory(pid) as reader:
#       reader.read(addr, size) / reader.write(addr, data) / reader.image_path
import ctypes
from ctypes import wintypes
import os
import threading
import time

from .memory import MemoryReadError, check_range

# Re-export the snapshot-based module lookup (no process handle required).
from .win32_memory import find_module, ProcessModule  # noqa: F401

SECTION_NAME = "\\BaseNamedObjects\\KmRwShared"
SHARED_SIZE = 0x400000          # 4 MB, matches the driver
DATA_OFFSET = 0x400             # data area begins 1 KB in, matches the driver

CMD_READ = 1
CMD_WRITE = 2
CMD_IMAGE_PATH = 3

STATUS_BUSY = 0
STATUS_DONE = 1
STATUS_ERROR = 2

SECTION_MAP_READ = 0x0004
SECTION_MAP_WRITE = 0x0002
OBJ_CASE_INSENSITIVE = 0x40
VIEW_SHARE = 2
PAGE_READWRITE = 0x04


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT),
                ("MaximumLength", wintypes.USHORT),
                ("Buffer", ctypes.c_wchar_p)]


class _OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_ulong),
                ("RootDirectory", ctypes.c_void_p),
                ("ObjectName", ctypes.c_void_p),
                ("Attributes", ctypes.c_ulong),
                ("SecurityDescriptor", ctypes.c_void_p),
                ("SecurityQualityOfService", ctypes.c_void_p)]


class KM_SHARED(ctypes.Structure):
    _fields_ = [("Command", ctypes.c_long),
                ("Status", ctypes.c_long),
                ("ErrorCode", ctypes.c_long),
                ("Pid", ctypes.c_uint64),
                ("Address", ctypes.c_uint64),
                ("Size", ctypes.c_uint64)]


def _ntdll():
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    ntdll.NtOpenSection.restype = ctypes.c_long
    ntdll.NtOpenSection.argtypes = [ctypes.POINTER(wintypes.HANDLE),
                                    wintypes.DWORD,
                                    ctypes.POINTER(_OBJECT_ATTRIBUTES)]
    ntdll.NtMapViewOfSection.restype = ctypes.c_long
    ntdll.NtMapViewOfSection.argtypes = [wintypes.HANDLE, wintypes.HANDLE,
                                         ctypes.POINTER(ctypes.c_void_p),
                                         ctypes.c_ulonglong, ctypes.c_size_t,
                                         ctypes.c_void_p,
                                         ctypes.POINTER(ctypes.c_size_t),
                                         wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    ntdll.NtUnmapViewOfSection.restype = ctypes.c_long
    ntdll.NtUnmapViewOfSection.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    return ntdll


class KernelProcessMemory:
    """Own a mapped view of the driver's shared section; read/write via it."""

    def __init__(self, pid: int):
        if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
            raise ValueError("pid must be a positive DWORD")
        self.pid = pid
        self._lock = threading.RLock()
        self._ntdll = _ntdll()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._current_process = kernel32.GetCurrentProcess()

        name = _UNICODE_STRING()
        name.Buffer = SECTION_NAME
        name.Length = len(SECTION_NAME) * 2
        name.MaximumLength = name.Length + 2

        oa = _OBJECT_ATTRIBUTES()
        oa.Length = ctypes.sizeof(_OBJECT_ATTRIBUTES)
        oa.ObjectName = ctypes.byref(name)
        oa.Attributes = OBJ_CASE_INSENSITIVE

        self._section = wintypes.HANDLE()
        st = self._ntdll.NtOpenSection(ctypes.byref(self._section),
                                       SECTION_MAP_READ | SECTION_MAP_WRITE,
                                       ctypes.byref(oa))
        if st != 0 or not self._section:
            raise MemoryReadError(st, f"driver shared section not open (NtOpenSection {st:#x}); "
                                       "is km_rw mapped and running?")

        self._view = ctypes.c_void_p()
        view_size = ctypes.c_size_t(SHARED_SIZE)
        st = self._ntdll.NtMapViewOfSection(self._section, self._current_process,
                                            ctypes.byref(self._view), 0, SHARED_SIZE,
                                            None, ctypes.byref(view_size),
                                            VIEW_SHARE, 0, PAGE_READWRITE)
        if st != 0 or not self._view.value:
            raise MemoryReadError(st, f"failed to map shared section (NtMapViewOfSection {st:#x})")

        self._shared = ctypes.cast(self._view, ctypes.POINTER(KM_SHARED))
        self._data = ctypes.cast(self._view.value + DATA_OFFSET, ctypes.c_void_p)
        self.dictionary_key_hashes = {}

    # -- request plumbing -------------------------------------------------

    def _run(self, command, address, data, size):
        with self._lock:
            sh = self._shared.contents
            sh.Pid = self.pid
            sh.Address = address
            sh.Size = size
            if command == CMD_WRITE and data:
                ctypes.memmove(self._data, data, size)
            sh.Status = STATUS_BUSY
            sh.Command = command
            deadline = time.perf_counter() + 5.0
            while self._shared.contents.Status == STATUS_BUSY:
                if time.perf_counter() > deadline:
                    raise MemoryReadError(0x102, "kernel command timed out")
                time.sleep(0.0005)
            if self._shared.contents.Status != STATUS_DONE:
                err = self._shared.contents.ErrorCode
                raise MemoryReadError(err, f"kernel command failed (NTSTATUS {err:#x})")

    # -- public interface --------------------------------------------------

    def read(self, address: int, size: int) -> bytes:
        check_range(address, size)
        if not size:
            return b""
        self._run(CMD_READ, address, None, size)
        return ctypes.string_at(self._data, size)

    def write(self, address: int, data: bytes) -> None:
        data = bytes(data)
        check_range(address, len(data))
        if not data:
            return
        self._run(CMD_WRITE, address, data, len(data))

    @property
    def image_path(self) -> str:
        self._run(CMD_IMAGE_PATH, 0, None, 0)
        return ctypes.wstring_at(self._data)

    def close(self):
        with self._lock:
            if getattr(self, "_view", None) and self._view.value:
                self._ntdll.NtUnmapViewOfSection(self._current_process, self._view)
                self._view = ctypes.c_void_p()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
