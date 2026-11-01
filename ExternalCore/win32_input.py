# Python | ExternalCore/win32_input.py | Python 3.12+ x64 / Windows | foreground-gated relative SendInput.
"""Documented input path. No process memory writes or privilege changes.

Relative counts depend on Windows/game sensitivity and acceleration. They are not
guaranteed pixels or angles. Tests serialize packets or reject dispatch; no real
mouse event is sent by the test suite.
https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-sendinput
"""
import ctypes as C
import os
import time

from .aim import AimDecision


class MOUSEINPUT(C.Structure):
    _fields_ = [("dx", C.c_int32), ("dy", C.c_int32), ("mouseData", C.c_uint32),
                ("dwFlags", C.c_uint32), ("time", C.c_uint32), ("dwExtraInfo", C.c_uint64)]


class _INPUTUNION(C.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(C.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", C.c_uint32), ("data", _INPUTUNION)]


def movement_packet(dx: int, dy: int) -> INPUT:
    if any(type(v) is not int or not -32767 <= v <= 32767 for v in (dx, dy)):
        raise ValueError("relative movement must contain bounded integer counts")
    packet = INPUT()
    packet.type = 0
    packet.mi = MOUSEINPUT(dx, dy, 0, 1, 0, 0)  # MOUSEEVENTF_MOVE only.
    return packet


class WindowsInput:
    def __init__(self, *, activation_key=0x02, max_age_ms=100.0):
        if os.name != "nt" or C.sizeof(C.c_void_p) != 8:
            raise OSError("input adapter requires 64-bit Windows")
        if type(activation_key) is not int or not 1 <= activation_key <= 254:
            raise ValueError("invalid activation virtual key")
        if not isinstance(max_age_ms, (int, float)) or not 0 < max_age_ms <= 1000:
            raise ValueError("invalid input age bound")
        self.activation_key, self.max_age_ms = activation_key, max_age_ms
        self.api = C.WinDLL("user32", use_last_error=True)
        self.api.GetForegroundWindow.argtypes = []
        self.api.GetForegroundWindow.restype = C.c_void_p
        self.api.IsWindow.argtypes = [C.c_void_p]
        self.api.IsWindow.restype = C.c_int32
        self.api.GetAsyncKeyState.argtypes = [C.c_int32]
        self.api.GetAsyncKeyState.restype = C.c_int16
        self.api.GetWindowThreadProcessId.argtypes = [C.c_void_p, C.POINTER(C.c_uint32)]
        self.api.GetWindowThreadProcessId.restype = C.c_uint32
        self.api.SendInput.argtypes = [C.c_uint32, C.POINTER(INPUT), C.c_int]
        self.api.SendInput.restype = C.c_uint32

    def dispatch(self, decision: AimDecision, target_hwnd: int, *, expected_pid: int, now_ns=None) -> str:
        if not isinstance(decision, AimDecision):
            raise TypeError("decision must be an AimDecision")
        if type(target_hwnd) is not int or target_hwnd < 0:
            raise ValueError("target HWND must be a nonnegative integer")
        if type(expected_pid) is not int or not 1 <= expected_pid <= 0xFFFFFFFF:
            raise ValueError("expected PID must be an explicit positive DWORD")
        now_ns = time.perf_counter_ns() if now_ns is None else now_ns
        if type(now_ns) is not int or now_ns < 0:
            raise ValueError("dispatch timestamp must be a nonnegative integer")
        if decision.reason != "planned" or not (decision.dx or decision.dy):
            return "no_movement"
        age = now_ns - decision.captured_ns
        if age < 0 or age > self.max_age_ms * 1_000_000:
            return "stale_or_future_capture"
        if not target_hwnd or not self.api.IsWindow(target_hwnd) or self.api.GetForegroundWindow() != target_hwnd:
            return "target_not_foreground"
        owner = C.c_uint32()
        if not self.api.GetWindowThreadProcessId(target_hwnd, C.byref(owner)) or owner.value != expected_pid:
            return "target_window_owner_changed"
        if not self.api.GetAsyncKeyState(self.activation_key) & 0x8000:
            return "activation_released"
        packet = movement_packet(decision.dx, decision.dy)
        if self.api.SendInput(1, C.byref(packet), C.sizeof(packet)) != 1:
            raise OSError(getattr(C, "get_last_error", lambda: 0)(), "SendInput did not insert the movement event")
        return "sent"
