# Python | tests/test_input.py | Python 3.12+ unittest | input packets and rejection gates, no OS events sent.
import ctypes
import unittest

from ExternalCore.aim import AimDecision
from ExternalCore.scene import ObservationId
from ExternalCore.win32_input import INPUT, MOUSEINPUT, WindowsInput, movement_packet


class InputTests(unittest.TestCase):
    def test_x64_abi_and_relative_counts_packet(self):
        self.assertEqual(ctypes.sizeof(MOUSEINPUT), 32)
        self.assertEqual(ctypes.sizeof(INPUT), 40)
        self.assertEqual(INPUT.data.offset, 8)
        packet = movement_packet(-12, 7)
        self.assertEqual((packet.type, packet.mi.dx, packet.mi.dy, packet.mi.dwFlags, packet.mi.mouseData),
                         (0, -12, 7, 1, 0))
        for values in [(True, 0), (1.0, 0), (32768, 0)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                movement_packet(*values)

    def test_dispatch_checks_age_focus_activation_and_return_count(self):
        calls = []
        class FakeUser:
            foreground, pressed, inserted, pid = 123, 0x8000, 1, 999
            def IsWindow(self, hwnd): return True
            def GetForegroundWindow(self): return self.foreground
            def GetAsyncKeyState(self, key): return self.pressed
            def GetWindowThreadProcessId(self, hwnd, owner):
                ctypes.cast(owner, ctypes.POINTER(ctypes.c_uint32))[0] = self.pid
                return 5
            def SendInput(self, count, packets, size):
                packet = ctypes.cast(packets, ctypes.POINTER(INPUT)).contents
                calls.append((packet.mi.dx, packet.mi.dy, size))
                return self.inserted
        source = WindowsInput.__new__(WindowsInput)
        source.api, source.activation_key, source.max_age_ms = FakeUser(), 2, 100
        decision = AimDecision(ObservationId(1,2,3,4,5), 4, -3, 1_000_000_000, "planned")
        self.assertEqual(source.dispatch(decision, 123, expected_pid=999, now_ns=1_200_000_000), "stale_or_future_capture")
        self.assertEqual(source.dispatch(decision, 124, expected_pid=999, now_ns=1_000_000_000), "target_not_foreground")
        source.api.pressed = 0
        self.assertEqual(source.dispatch(decision, 123, expected_pid=999, now_ns=1_000_000_000), "activation_released")
        self.assertEqual(calls, [])
        for invalid in (float("nan"), float("inf"), True, -1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                source.dispatch(decision, 123, expected_pid=999, now_ns=invalid)
        source.api.pressed = 0x8000
        source.api.pid = 1000
        self.assertEqual(source.dispatch(decision, 123, expected_pid=999, now_ns=1_000_000_000), "target_window_owner_changed")
        source.api.pid = 999
        self.assertEqual(source.dispatch(decision, 123, expected_pid=999, now_ns=1_000_000_000), "sent")
        self.assertEqual(calls, [(4,-3,40)])  # FakeUser only; no system input call.
        source.api.inserted = 0
        with self.assertRaises(OSError):
            source.dispatch(decision, 123, expected_pid=999, now_ns=1_000_000_000)


if __name__ == "__main__":
    unittest.main()
