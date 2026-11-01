# Python | ExternalCore/win32_overlay.py | Python 3.12+ x64 / Windows | owned GDI overlay.
"""Owned, thread-affine Win32 GDI rendering; importing is safe on other OSes.

Black is the overlay transparency key. No process inspection or input APIs.
"""
import ctypes as C
from ctypes import wintypes as W
import os
import threading

MAX_DIMENSION = 8192
MAX_COMMANDS = 10000
OVERLAY_STYLE = 0x08000000 | 0x80 | 0x20 | 0x80000 | 0x8

class _PaintStruct(C.Structure):
    _fields_ = [('hdc', W.HDC), ('erase', W.BOOL), ('rect', W.RECT),
                ('restore', W.BOOL), ('update', W.BOOL), ('reserved', W.BYTE * 32)]


def _api():
    if os.name != 'nt' or C.sizeof(C.c_void_p) != 8:
        raise OSError('Native overlay requires 64-bit Windows')
    g, u = C.WinDLL('gdi32', use_last_error=True), C.WinDLL('user32', use_last_error=True)
    signatures = [
        (g, 'CreateCompatibleDC', W.HDC, [W.HDC]),
        (g, 'CreateCompatibleBitmap', W.HBITMAP, [W.HDC, C.c_int, C.c_int]),
        (g, 'SelectObject', W.HANDLE, [W.HDC, W.HANDLE]),
        (g, 'DeleteObject', W.BOOL, [W.HANDLE]), (g, 'DeleteDC', W.BOOL, [W.HDC]),
        (g, 'PatBlt', W.BOOL, [W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,W.DWORD]),
        (g, 'CreatePen', W.HANDLE, [C.c_int,C.c_int,W.DWORD]),
        (g, 'GetStockObject', W.HANDLE, [C.c_int]),
        (g, 'MoveToEx', W.BOOL, [W.HDC,C.c_int,C.c_int,C.c_void_p]),
        (g, 'LineTo', W.BOOL, [W.HDC,C.c_int,C.c_int]),
        (g, 'Ellipse', W.BOOL, [W.HDC,C.c_int,C.c_int,C.c_int,C.c_int]),
        (g, 'SetTextColor', W.DWORD, [W.HDC,W.DWORD]),
        (g, 'SetBkMode', C.c_int, [W.HDC,C.c_int]),
        (g, 'TextOutW', W.BOOL, [W.HDC,C.c_int,C.c_int,W.LPCWSTR,C.c_int]),
        (g, 'GetPixel', W.DWORD, [W.HDC,C.c_int,C.c_int]),
        (g, 'BitBlt', W.BOOL, [W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,W.HDC,C.c_int,C.c_int,W.DWORD]),
        (u, 'GetDC', W.HDC, [W.HWND]), (u, 'ReleaseDC', C.c_int, [W.HWND,W.HDC]),
        (u, 'CreateWindowExW', W.HWND, [W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p]),
        (u, 'DestroyWindow', W.BOOL, [W.HWND]),
        (u, 'IsWindow', W.BOOL, [W.HWND]),
        (u, 'SetLayeredWindowAttributes', W.BOOL, [W.HWND,W.DWORD,W.BYTE,W.DWORD]),
        (u, 'ShowWindow', W.BOOL, [W.HWND,C.c_int]),
        (u, 'GetWindowLongW', W.LONG, [W.HWND,C.c_int]),
        (u, 'SetWindowLongPtrW', C.c_ssize_t, [W.HWND,C.c_int,C.c_ssize_t]),
        (u, 'CallWindowProcW', C.c_ssize_t, [C.c_ssize_t,W.HWND,W.UINT,W.WPARAM,W.LPARAM]),
        (u, 'ValidateRect', W.BOOL, [W.HWND,C.c_void_p]),
        (u, 'BeginPaint', W.HDC, [W.HWND,C.POINTER(_PaintStruct)]),
        (u, 'EndPaint', W.BOOL, [W.HWND,C.POINTER(_PaintStruct)]),
        (u, 'PeekMessageW', W.BOOL, [C.POINTER(W.MSG),W.HWND,W.UINT,W.UINT,W.UINT]),
        (u, 'TranslateMessage', W.BOOL, [C.POINTER(W.MSG)]),
        (u, 'DispatchMessageW', C.c_ssize_t, [C.POINTER(W.MSG)]),
    ]
    for dll, name, result, args in signatures:
        fn = getattr(dll, name); fn.restype = result; fn.argtypes = args
    return g, u


def _check(value):
    if not value:
        raise C.WinError(C.get_last_error())
    return value


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'Expected integer in [{low}, {high}]')
    return value


class GdiSurface:
    def __init__(self, width, height):
        self.width = _integer(width, 1, MAX_DIMENSION)
        self.height = _integer(height, 1, MAX_DIMENSION)
        self._thread = threading.get_ident()
        self.g, self.u = _api()
        self.dc = self.bitmap = self._old = None
        screen = _check(self.u.GetDC(None))
        try:
            self.dc = _check(self.g.CreateCompatibleDC(screen))
            self.bitmap = _check(self.g.CreateCompatibleBitmap(screen, width, height))
            self._old = _check(self.g.SelectObject(self.dc, self.bitmap))
            self.draw([])
        except BaseException:
            self.close()
            raise
        finally:
            self.u.ReleaseDC(None, screen)

    def _alive(self):
        if threading.get_ident() != self._thread:
            raise RuntimeError('GDI objects must be used on their creating thread')
        if not self.dc:
            raise RuntimeError('Surface is closed')

    def draw(self, commands):
        self._alive()
        normalized = []
        for command in commands:
            if len(normalized) >= MAX_COMMANDS:
                raise ValueError('Too many drawing commands')
            if not isinstance(command, dict):
                raise ValueError('Drawing commands must be dictionaries')
            kind = command.get('kind')
            fields = {'line': ('x1','y1','x2','y2'), 'circle': ('x','y','radius'), 'text': ('x','y')}.get(kind)
            if fields is None:
                raise ValueError('Unknown drawing command')
            values = [_integer(command.get(k), 0 if k == 'radius' else -32768, 32767) for k in fields]
            color = command.get('color')
            if not isinstance(color, (tuple, list)) or len(color) != 3:
                raise ValueError('Color must contain three RGB bytes')
            rgb = sum(_integer(v, 0, 255) << (8*i) for i,v in enumerate(color))
            width = _integer(command.get('width', 1), 1, 256)
            text = command.get('text', '')
            if kind == 'text' and (not isinstance(text, str) or len(text) > 4096):
                raise ValueError('Text must be a string of at most 4096 characters')
            try:
                units = len(text.encode('utf-16-le')) // 2 if kind == 'text' else 0
            except UnicodeEncodeError as exc:
                raise ValueError('Text contains an unpaired UTF-16 surrogate') from exc
            normalized.append((kind, values, rgb, width, text, units))
        _check(self.g.PatBlt(self.dc, 0, 0, self.width, self.height, 0x42))
        for kind, v, rgb, width, text, units in normalized:
            if kind == 'text':
                self.g.SetTextColor(self.dc, rgb); self.g.SetBkMode(self.dc, 1)
                _check(self.g.TextOutW(self.dc, *v, text, units))
                continue
            pen = _check(self.g.CreatePen(0, width, rgb))
            old = _check(self.g.SelectObject(self.dc, pen))
            brush = None
            try:
                if kind == 'line':
                    _check(self.g.MoveToEx(self.dc, v[0], v[1], None))
                    _check(self.g.LineTo(self.dc, v[2], v[3]))
                else:
                    brush = _check(self.g.SelectObject(self.dc, self.g.GetStockObject(5)))
                    x,y,r = v
                    _check(self.g.Ellipse(self.dc, x-r,y-r,x+r+1,y+r+1))
            finally:
                if brush: self.g.SelectObject(self.dc, brush)
                self.g.SelectObject(self.dc, old)
                self.g.DeleteObject(pen)

    def pixel(self, x, y):
        self._alive()
        _integer(x, 0, self.width-1); _integer(y, 0, self.height-1)
        value = self.g.GetPixel(self.dc, x, y)
        if value == 0xffffffff: raise C.WinError(C.get_last_error())
        return tuple((value >> (8*i)) & 255 for i in range(3))

    def close(self):
        if threading.get_ident() != self._thread:
            raise RuntimeError('Close must run on creating thread')
        if self.dc and self._old: self.g.SelectObject(self.dc, self._old)
        if self.bitmap: self.g.DeleteObject(self.bitmap)
        if self.dc: self.g.DeleteDC(self.dc)
        self.dc = self.bitmap = self._old = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class OverlayWindow:
    def __init__(self, width, height, left=0, top=0, visible=False, title='BloodStrikeExternal'):
        self.surface = GdiSurface(width, height)
        self.hwnd = None
        self.u, self.g = self.surface.u, self.surface.g
        try:
            _integer(left, -32768, 32767); _integer(top, -32768, 32767)
            self.hwnd = _check(self.u.CreateWindowExW(OVERLAY_STYLE, 'STATIC', title, 0x80000000,
                left, top, width, height, None, None, None, None))
            callback_type = C.WINFUNCTYPE(C.c_ssize_t, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
            def procedure(hwnd, message, wparam, lparam):
                if message == 0x14: return 1  # WM_ERASEBKGND
                if message == 0x0f:  # WM_PAINT: restore the retained surface
                    paint = _PaintStruct()
                    dc = self.u.BeginPaint(hwnd, C.byref(paint))
                    if dc:
                        self.g.BitBlt(dc, 0, 0, width, height, self.surface.dc, 0, 0, 0xcc0020)
                    self.u.EndPaint(hwnd, C.byref(paint))
                    return 0
                return self.u.CallWindowProcW(self._previous_proc, hwnd, message, wparam, lparam)
            self._procedure = callback_type(procedure)
            self._previous_proc = _check(self.u.SetWindowLongPtrW(self.hwnd, -4, C.cast(self._procedure, C.c_void_p).value))
            _check(self.u.SetLayeredWindowAttributes(self.hwnd, 0, 255, 1))
            if visible: self.u.ShowWindow(self.hwnd, 4)
        except BaseException:
            self.close(); raise

    def draw(self, commands):
        self.surface.draw(commands)
        if not self.hwnd or not self.u.IsWindow(self.hwnd): raise RuntimeError('Window is closed')
        dc = _check(self.u.GetDC(self.hwnd))
        try:
            _check(self.g.BitBlt(dc, 0, 0, self.surface.width, self.surface.height, self.surface.dc, 0, 0, 0xcc0020))
        finally: self.u.ReleaseDC(self.hwnd, dc)

    def pump(self):
        if threading.get_ident() != self.surface._thread: raise RuntimeError('Pump must run on creating thread')
        if not self.hwnd or not self.u.IsWindow(self.hwnd): return False
        msg = W.MSG()
        for _ in range(256):
            if not self.u.PeekMessageW(C.byref(msg), self.hwnd, 0, 0, 1): break
            self.u.TranslateMessage(C.byref(msg)); self.u.DispatchMessageW(C.byref(msg))
        return bool(self.u.IsWindow(self.hwnd))

    def close(self):
        if threading.get_ident() != self.surface._thread: raise RuntimeError('Close must run on creating thread')
        if self.hwnd:
            if self.u.IsWindow(self.hwnd): _check(self.u.DestroyWindow(self.hwnd))
            self.hwnd = None
        self.surface.close()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
