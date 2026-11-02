# Python | ExternalCore/live.py | Python 3.12+ x64 / Windows | explicit PID/window ESP observation loop.
"""No automatic process discovery. This module is not run by tests against a game.

Displays guarded origins and candidate labels. Optional aim dispatch requires an
explicit calibrated profile, activation key, fresh frame and foreground target.
"""
import ctypes as C
import math
import os
from pathlib import Path
import time

from .build import ModuleIdentity, verify_sample
from .pipeline import process_frame
from .snapshot import write_json
from .aim import AimProfile
from .memory import MemoryReadError
from .registry import RegistryReadError


def watch(pid, sample_path, hwnd, output, *, seconds=10.0, fps=30.0, show=False,
          allow_motion=False,max_age_ms=100.0,aim=False,counts_per_pixel=None,
          activation_key=0x02,require_visible=True,aim_radius=180.0,tau_ms=70.0,
          max_step_counts=25.0,target_local_y=1.55,calibration_fov=None,
          runtime_controls=None,stop_event=None):
    if any(not isinstance(v, (int,float)) or not math.isfinite(v) for v in (seconds, fps)):
        raise ValueError("duration/fps must be finite")
    if not 0 < seconds <= 3600 or not 1 <= fps <= 120:
        raise ValueError("duration/fps outside supported bounds")
    if type(aim) is not bool:raise TypeError('aim must be bool')
    if type(activation_key) is not int or not 1<=activation_key<=254 or activation_key==0x77:
        raise ValueError('activation key must be a virtual key other than exit key F8')
    if aim and counts_per_pixel is None:
        raise ValueError('aim requires measured counts_per_pixel calibration')
    if calibration_fov is not None and (not math.isfinite(calibration_fov) or not 0<calibration_fov<180):
        raise ValueError('invalid calibration FOV')
    profile=AimProfile(max_age_ms=max_age_ms,counts_per_pixel=counts_per_pixel,
        require_visible=require_visible,radius_px=aim_radius,tau_ms=tau_ms,
        max_step_counts=max_step_counts)
    from ctypes import wintypes as W
    from .win32_memory import WindowsProcessMemory, find_module
    from .win32_overlay import OverlayWindow
    from .win32_input import WindowsInput
    input_source=WindowsInput(activation_key=activation_key,max_age_ms=max_age_ms) if aim else None
    sample = verify_sample(sample_path)
    user = C.WinDLL("user32", use_last_error=True)
    user.IsWindow.argtypes = [W.HWND]; user.IsWindow.restype = W.BOOL
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetWindowThreadProcessId.restype = W.DWORD
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]; user.GetClientRect.restype = W.BOOL
    user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]; user.ClientToScreen.restype = W.BOOL
    user.IsIconic.argtypes = [W.HWND]; user.IsIconic.restype = W.BOOL
    user.GetForegroundWindow.argtypes = []; user.GetForegroundWindow.restype = W.HWND
    user.GetAsyncKeyState.argtypes=[C.c_int];user.GetAsyncKeyState.restype=C.c_short
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
            attempts,read_failures,consecutive_failures,packets_sent=0,0,0,0
            locked_target=None
            while time.perf_counter() - start < seconds:
                if stop_event is not None and stop_event.is_set():break
                if user.GetAsyncKeyState(0x77)&0x8000:  # F8 closes this observation loop.
                    break
                cycle = time.perf_counter()
                if not user.GetWindowThreadProcessId(hwnd, C.byref(owner)) or owner.value != pid:
                    raise ValueError("target window was destroyed or its owner changed")
                attempts+=1
                controls=runtime_controls.snapshot() if runtime_controls is not None else None
                enabled=aim and (controls is None or controls['aim'])
                active=bool(enabled and user.GetForegroundWindow()==hwnd and not user.IsIconic(hwnd)
                            and user.GetAsyncKeyState(activation_key)&0x8000)
                if not active:locked_target=None
                try:
                    frame = process_frame(reader, identity, dt_ms=min(1000,(cycle-last)*1000), active=active,
                                          require_render_input=True,allow_motion=allow_motion,profile=profile,
                                          target_local_y=target_local_y,locked_target=locked_target,
                                          refresh_geometry=True)
                except (RegistryReadError,MemoryReadError) as exc:
                    locked_target=None
                    read_failures+=1;consecutive_failures+=1
                    if window:
                        window.close();window=None;geometry=None
                    write_json(output,{'format':'bloodstrike-observation-status-v1',
                        'status':'retrying_read','pid':pid,'module':identity,
                        'error_type':type(exc).__name__,'error':str(exc),
                        'frames':frames,'attempts':attempts,'read_failures':read_failures,
                        'packets_sent':packets_sent,
                        'consecutive_failures':consecutive_failures,'input_dispatched':False,
                        'gameplay_validated':False})
                    last=cycle
                    time.sleep(max(0.0,1/fps-(time.perf_counter()-cycle)))
                    continue
                consecutive_failures=0
                locked_target=frame.aim.target if active and frame.render_status=='fresh' else None
                last = cycle
                client, corner = W.RECT(), W.POINT()
                if not user.GetClientRect(hwnd, C.byref(client)) or not user.ClientToScreen(hwnd, C.byref(corner)):
                    raise C.WinError(C.get_last_error())
                size = (client.right-client.left, client.bottom-client.top)
                aligned = size == (frame.scene.width, frame.scene.height)
                foreground = user.GetForegroundWindow() == hwnd and not user.IsIconic(hwnd)
                current = (*size, corner.x, corner.y)
                if runtime_controls is not None:
                    controls=runtime_controls.snapshot()
                    enabled=aim and controls['aim']
                    if not enabled:locked_target=None
                input_status='disabled'
                if input_source is not None and enabled:
                    if calibration_fov is not None and abs(frame.capture.camera.camera.field_of_view-calibration_fov)>0.1:
                        input_status='calibration_fov_mismatch';locked_target=None
                    else:
                        input_status=input_source.dispatch(frame.aim,hwnd,expected_pid=pid) if aligned and foreground else 'window_not_aligned_or_foreground'
                    packets_sent+=input_status=='sent'
                commands=frame.commands
                if controls is not None:
                    from .controls import render_controls
                    commands=render_controls(frame,controls,reader=reader)
                if show and aligned and foreground and (controls is None or controls['esp']):
                    if geometry != current:
                        if window: window.close()
                        window = OverlayWindow(*size, left=corner.x, top=corner.y, visible=True)
                        geometry = current
                    window.draw(commands)
                    if not window.pump():
                        break
                elif window:
                    window.close(); window = None; geometry = None
                frames += 1
                write_json(output, {"format": "bloodstrike-pipeline-frame-v1", "source": "win32_read_only",
                                   "pid": pid, "module": identity, "frame": frame,
                                   "window_size_matches_candidate_camera": aligned,
                                   "target_foreground":foreground,
                                   "max_age_ms":max_age_ms,
                                   "attempts":attempts,"read_failures":read_failures,
                                   "input_status":input_status,"packets_sent":packets_sent,
                                   "controls":controls,"rendered_commands":commands,
                                   "gameplay_validated": False, "frames": frames,
                                   "input_dispatched": input_status=='sent'})
                time.sleep(max(0.0, 1/fps - (time.perf_counter()-cycle)))
            return frames
    finally:
        if window: window.close()
        user.SetThreadDpiAwarenessContext(previous_dpi)
