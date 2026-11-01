# Python | tests/test_overlay_native.py | Python 3.12+ unittest | owned hidden GDI windows only.
import os
import ctypes
import threading
import unittest

from ExternalCore.win32_overlay import GdiSurface, OverlayWindow, OVERLAY_STYLE, MAX_COMMANDS


@unittest.skipUnless(os.name == 'nt', 'requires Windows GDI')
class NativeOverlayTests(unittest.TestCase):
    def test_pixels_clear_clipping_circle_and_text(self):
        with GdiSurface(96, 64) as surface:
            surface.draw([
                dict(kind='line', x1=-20, y1=10, x2=120, y2=10, color=[250, 30, 10]),
                dict(kind='circle', x=40, y=35, radius=10, color=[0, 255, 0]),
                dict(kind='text', x=60, y=30, text='Hi', color=[0, 0, 255]),
            ])
            self.assertEqual(surface.pixel(0, 10), (250, 30, 10))
            self.assertEqual(surface.pixel(95, 10), (250, 30, 10))
            self.assertEqual(surface.pixel(40, 35), (0, 0, 0))
            self.assertTrue(any(surface.pixel(x,y) == (0,255,0) for x in range(28,53) for y in range(23,48)))
            self.assertTrue(any(surface.pixel(x,y) == (0,0,255) for x in range(60,90) for y in range(30,55)))
            surface.draw([])
            self.assertEqual(surface.pixel(0,10), (0,0,0))
        surface.close()
        with self.assertRaises(RuntimeError): surface.pixel(0,0)

    def test_validation_is_atomic_and_thread_affine(self):
        with GdiSurface(16,16) as surface:
            surface.draw([dict(kind='line',x1=0,y1=0,x2=15,y2=0,color=[1,2,3])])
            for command in [dict(kind='wat'), dict(kind='text',x=0,y=0,text=42,color=[1,2,3]),
                            dict(kind='text',x=0,y=0,text='\ud800',color=[1,2,3]),
                            dict(kind='circle',x=0,y=0,radius=-1,color=[1,2,3])]:
                with self.assertRaises(ValueError): surface.draw([command])
            self.assertEqual(surface.pixel(0,0), (1,2,3))
            with self.assertRaises(ValueError):
                surface.draw([dict(kind='line',x1=0,y1=0,x2=1,y2=1,color=[1,2,3])] * (MAX_COMMANDS+1))
            errors = []
            def other_thread():
                try: surface.close()
                except RuntimeError: errors.append(True)
            thread = threading.Thread(target=other_thread); thread.start(); thread.join()
            self.assertEqual(errors, [True])
        for size in [0,8193,True]:
            with self.assertRaises(ValueError): GdiSurface(size,16)

    def test_hidden_window_styles_and_cleanup(self):
        with OverlayWindow(64,48) as window:
            hwnd = window.hwnd
            self.assertTrue(window.u.IsWindow(hwnd))
            self.assertEqual(window.u.GetWindowLongW(hwnd,-20) & OVERLAY_STYLE, OVERLAY_STYLE)
            self.assertFalse(window.u.GetWindowLongW(hwnd,-16) & 0x10000000)
            window.draw([dict(kind='line',x1=1,y1=2,x2=40,y2=2,color=[255,0,0])])
            self.assertTrue(window.pump())
            # Hidden HWND DCs have no visible pixels; inspect its retained GDI bitmap.
            self.assertEqual(window.surface.pixel(5,2), (255,0,0))
        self.assertFalse(window.u.IsWindow(hwnd))
        self.assertFalse(window.pump())
        window.close()

    def test_repeated_close_releases_gdi_objects(self):
        user = ctypes.WinDLL('user32')
        kernel = ctypes.WinDLL('kernel32')
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        user.GetGuiResources.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user.GetGuiResources.restype = ctypes.c_uint
        process = kernel.GetCurrentProcess()
        with GdiSurface(8,8): pass  # warm up native libraries
        before = user.GetGuiResources(process, 0)
        for _ in range(20):
            with OverlayWindow(32,32) as window:
                window.draw([dict(kind='circle',x=16,y=16,radius=5,color=[1,2,3])])
            window.close()
        self.assertEqual(user.GetGuiResources(process, 0), before)


if __name__ == '__main__': unittest.main()
