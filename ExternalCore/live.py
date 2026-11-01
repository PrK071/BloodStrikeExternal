# Python | ExternalCore/live.py | Python 3.12+ x64 / Windows | explicit PID/window ESP observation loop.
"""No automatic process discovery. This module is not run by tests against a game.

Displays guarded origins and candidate labels; no opponent/gain fields are invented and this
loop dispatches no input. Input planning/dispatch adapters are separate modules.
"""
import ctypes as C
import math
import os
from pathlib import Path
import time

from .build import ModuleIdentity, verify_sample
from .pipeline import process_frame
from .snapshot import write_json


def watch(pid, sample_path, hwnd, output, *, seconds=10.0, fps=30.0, show=False):
    if any(not isinstance(v, (int,float)) or not math.isfinite(v) for v in (seconds, fps)):
        raise ValueError("duration/fps must be finite")
    if not 0 < seconds <= 3600 or not 1 <= fps <= 120:
        raise ValueError("duration/fps outside supported bounds")
    from ctypes import wintypes as W
    from .win32_memory import WindowsProcessMemory, find_module
    from .win32_overlay import OverlayWindow
    sample = verify_sample(sample_path)
    user = C.WinDLL("user32", use_last_error=True)
    user.IsWindow.argtypes = [W.HWND]; user.IsWindow.restype = W.BOOL
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetWindowThreadProcessId.restype = W.DWORD
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]; user.GetClientRect.restype = W.BOOL
    user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]; user.ClientToScreen.restype = W.BOOL
    user.IsIconic.argtypes = [W.HWND]; user.IsIconic.restype = W.BOOL
    user.GetForegroundWindow.argtypes = []; user.GetForegroundWindow.restype = W.HWND
    user.SetThreadDpiAwarenessContext.argtypes = [C.c_void_p]
    user.SetThreadDpiAwarenessContext.restype = C.c_void_p
    owner = W.DWORD()
    if not user.IsWindow(hwnd) or not user.GetWindowThreadProcessId(hwnd, C.byref(owner)) or owner.value != pid:
        raise ValueError("HWND is not an existing window of the explicitly selected PID")
    previous_dpi = user.SetThreadDpiAwarenessContext(C.c_void_p(-4))
    if not previous_dpi:
        raise C.WinError(C.get_last_error())
    window = None
    geometry = None
    try:
        with WindowsProcessMemory(pid) as reader:
            if os.path.normcase(os.path.realpath(reader.image_path)) != os.path.normcase(sample["path"]):
                raise ValueError("selected PID executable path differs from the verified sample")
            module = find_module(pid, sample["path"])
            if module.size != sample["image_size"]:
                raise ValueError("mapped module size differs from the verified sample")
            identity = ModuleIdentity(module.base, module.size, sample["sha256"])
            start, last, frames = time.perf_counter(), time.perf_counter(), 0
            while time.perf_counter() - start < seconds:
                cycle = time.perf_counter()
                frame = process_frame(reader, identity, dt_ms=min(1000,(cycle-last)*1000), active=False,
                                      require_render_input=True)
                last = cycle
                if not user.GetWindowThreadProcessId(hwnd, C.byref(owner)) or owner.value != pid:
                    raise ValueError("target window was destroyed or its owner changed")
                client, corner = W.RECT(), W.POINT()
                if not user.GetClientRect(hwnd, C.byref(client)) or not user.ClientToScreen(hwnd, C.byref(corner)):
                    raise C.WinError(C.get_last_error())
                size = (client.right-client.left, client.bottom-client.top)
                aligned = size == (frame.scene.width, frame.scene.height)
                foreground = user.GetForegroundWindow() == hwnd and not user.IsIconic(hwnd)
                current = (*size, corner.x, corner.y)
                if show and aligned and foreground:
                    if geometry != current:
                        if window: window.close()
                        window = OverlayWindow(*size, left=corner.x, top=corner.y, visible=True)
                        geometry = current
                    window.draw(frame.commands)
                    if not window.pump():
                        break
                elif window:
                    window.close(); window = None; geometry = None
                frames += 1
                write_json(output, {"format": "bloodstrike-pipeline-frame-v1", "source": "win32_read_only",
                                   "pid": pid, "module": identity, "frame": frame,
                                   "window_size_matches_candidate_camera": aligned,
                                   "gameplay_validated": False, "frames": frames, "input_dispatched": False})
                time.sleep(max(0.0, 1/fps - (time.perf_counter()-cycle)))
            return frames
    finally:
        if window: window.close()
        user.SetThreadDpiAwarenessContext(previous_dpi)
