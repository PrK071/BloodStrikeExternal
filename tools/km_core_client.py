#!/usr/bin/env python3
# Python | tools/km_core_client.py | Python 3.12+ x64 / Windows
"""Client for the km_core driver: version, state and capabilities.

Queries only. There is no process memory access in this file, and the driver
exposes none: every IOCTL takes a fixed 0x10-byte header and returns a fixed
0x10-byte answer.

Usage:
    python tools/km_core_client.py [device-path]

Exit codes:
    0  all three queries succeeded
    1  device could not be opened, a call failed, or the reply was rejected
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys

DEVICE_PATH = r"\\.\KmCore"

# --------------------------------------------------------------------------
# ABI constants. These mirror km_core/km_core.c; a mismatch is caught by the
# layout checks below and by the AbiVersion check at runtime.
# --------------------------------------------------------------------------
ABI_VERSION = 1

FILE_DEVICE_UNKNOWN = 0x22
METHOD_BUFFERED = 0
FILE_READ_DATA = 0x0001
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

STATE_NAMES = {
    0: "initializing",
    1: "ready",
    2: "degraded",
}

CAPABILITY_NAMES = (
    (0x00000001, "get_version"),
    (0x00000002, "get_state"),
    (0x00000004, "get_caps"),
)


def _ctl(function: int, access: int = FILE_READ_DATA) -> int:
    """CTL_CODE(DeviceType, Function, Method, Access) from winioctl.h."""
    return ((FILE_DEVICE_UNKNOWN << 16) | (access << 14) |
            (function << 2) | METHOD_BUFFERED)


IOCTL_KM_GET_VERSION = _ctl(0x800)
IOCTL_KM_GET_STATE = _ctl(0x801)
IOCTL_KM_GET_CAPS = _ctl(0x802)


class KmCoreError(RuntimeError):
    """The driver answered something this client does not accept."""


# --------------------------------------------------------------------------
# Structures: 0x10 bytes each, no pointers, no variable-length fields.
# --------------------------------------------------------------------------
class KM_QUERY(ctypes.Structure):
    _fields_ = [("AbiVersion", ctypes.c_uint32),
                ("StructSize", ctypes.c_uint32),
                ("Command", ctypes.c_uint32),
                ("Reserved", ctypes.c_uint32)]


class KM_VERSION(ctypes.Structure):
    _fields_ = [("AbiVersion", ctypes.c_uint32),
                ("StructSize", ctypes.c_uint32),
                ("DriverVersion", ctypes.c_uint32),
                ("BuildNumber", ctypes.c_uint32)]


class KM_STATE(ctypes.Structure):
    _fields_ = [("State", ctypes.c_uint32),
                ("UptimeSeconds", ctypes.c_uint32),
                ("RequestsServed", ctypes.c_uint64)]


class KM_CAPS(ctypes.Structure):
    _fields_ = [("StructSize", ctypes.c_uint32),
                ("CapabilityMask", ctypes.c_uint32),
                ("MaxRequest", ctypes.c_uint32),
                ("Reserved", ctypes.c_uint32)]


def _check_layout() -> None:
    """Mirror of the C_ASSERTs in km_core.c.

    Explicit checks instead of `assert`, so the guard also holds under
    `python -O`.
    """
    for struct_type in (KM_QUERY, KM_VERSION, KM_STATE, KM_CAPS):
        size = ctypes.sizeof(struct_type)
        if size != 0x10:
            raise RuntimeError(f"{struct_type.__name__} is {size:#x} bytes, expected 0x10")
    if KM_QUERY.Command.offset != 0x08:
        raise RuntimeError("KM_QUERY.Command is not at 0x08")
    if KM_STATE.RequestsServed.offset != 0x08:
        raise RuntimeError("KM_STATE.RequestsServed is not at 0x08")
    if KM_CAPS.CapabilityMask.offset != 0x04:
        raise RuntimeError("KM_CAPS.CapabilityMask is not at 0x04")


_check_layout()


class KmCore:
    """One device handle; every query is one independent DeviceIoControl."""

    def __init__(self, path: str = DEVICE_PATH):
        self._path = path
        self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self._k32.CreateFileW.restype = wintypes.HANDLE
        self._k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                          wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.DWORD,
                                          wintypes.HANDLE]
        self._k32.DeviceIoControl.restype = wintypes.BOOL
        self._k32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                              wintypes.LPVOID, wintypes.DWORD,
                                              wintypes.LPVOID, wintypes.DWORD,
                                              ctypes.POINTER(wintypes.DWORD),
                                              wintypes.LPVOID]
        self._k32.CloseHandle.restype = wintypes.BOOL
        self._k32.CloseHandle.argtypes = [wintypes.HANDLE]

        # FILE_READ_DATA only: the minimum the IOCTLs require, and exactly what
        # the driver checks for in IRP_MJ_CREATE.
        handle = self._k32.CreateFileW(path, FILE_READ_DATA, 0, None,
                                       OPEN_EXISTING, 0, None)
        if not handle or handle == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        self._handle = handle

    # -- transport -----------------------------------------------------

    def _query(self, code: int, response_type):
        query = KM_QUERY(ABI_VERSION, ctypes.sizeof(KM_QUERY), code, 0)
        response = response_type()
        returned = wintypes.DWORD(0)

        ok = self._k32.DeviceIoControl(self._handle, code,
                                       ctypes.byref(query), ctypes.sizeof(query),
                                       ctypes.byref(response), ctypes.sizeof(response),
                                       ctypes.byref(returned), None)
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

        expected = ctypes.sizeof(response)
        if returned.value != expected:
            raise KmCoreError(f"short reply: {returned.value} of {expected} bytes")
        if hasattr(response, "StructSize") and response.StructSize != expected:
            raise KmCoreError(f"reply reports struct size {response.StructSize:#x}, "
                              f"expected {expected:#x}")
        return response

    # -- public interface ----------------------------------------------

    def get_version(self) -> KM_VERSION:
        version = self._query(IOCTL_KM_GET_VERSION, KM_VERSION)
        if version.AbiVersion != ABI_VERSION:
            raise KmCoreError(f"ABI mismatch: driver {version.AbiVersion}, "
                              f"client {ABI_VERSION}")
        return version

    def get_state(self) -> KM_STATE:
        return self._query(IOCTL_KM_GET_STATE, KM_STATE)

    def get_caps(self) -> KM_CAPS:
        return self._query(IOCTL_KM_GET_CAPS, KM_CAPS)

    # -- lifetime ------------------------------------------------------

    def close(self) -> None:
        handle = getattr(self, "_handle", None)
        if handle:
            self._k32.CloseHandle(handle)
            self._handle = None

    def __enter__(self) -> "KmCore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def _format_version(version: int) -> str:
    return f"{(version >> 16) & 0xFFFF}.{version & 0xFFFF}"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = args[0] if args else DEVICE_PATH

    try:
        with KmCore(path) as device:
            version = device.get_version()
            state = device.get_state()
            caps = device.get_caps()
    except (OSError, KmCoreError) as exc:
        winerror = getattr(exc, "winerror", None)
        detail = f" (winerror {winerror})" if winerror else ""
        print(f"km_core: {exc}{detail}", file=sys.stderr)
        return 1

    capabilities = [name for bit, name in CAPABILITY_NAMES
                    if caps.CapabilityMask & bit]

    print(f"device   : {path}")
    print(f"driver   : {_format_version(version.DriverVersion)} "
          f"build {version.BuildNumber}")
    print(f"abi      : {version.AbiVersion}")
    print(f"state    : {STATE_NAMES.get(state.State, state.State)} "
          f"({state.UptimeSeconds}s uptime, {state.RequestsServed} requests)")
    print(f"caps     : {', '.join(capabilities) or '(none)'}")
    print(f"max xfer : {caps.MaxRequest} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
