# Python | tests/test_win32_integration.py | Python 3.12+ unittest | owned Windows child process only.
"""Real OpenProcess/ReadProcessMemory integration, never a game PID."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import unittest

from ExternalCore.build import ModuleIdentity
from ExternalCore.entity_position import SAMPLE_SHA256
from ExternalCore.memory import MemoryReadError
from ExternalCore.registry import collect_registry
from ExternalCore.win32_memory import WindowsProcessMemory, find_module


@unittest.skipUnless(os.name == "nt", "Windows native integration; required in the Windows CI job")
class Win32IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("native_fixture.py"))],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True)
        self.addCleanup(self.stop_child)
        self.lines = queue.Queue()
        def consume():
            for line in self.child.stdout:
                self.lines.put(line)
        self.thread = threading.Thread(target=consume, daemon=True)
        self.thread.start()
        line = self.lines.get(timeout=15)
        self.metadata = json.loads(line)
        self.module = ModuleIdentity(self.metadata["base"], 0x94E9000, SAMPLE_SHA256)
        self.reader = WindowsProcessMemory(self.child.pid)
        self.addCleanup(self.reader.close)

    def stop_child(self):
        if self.child.poll() is None:
            try:
                self.child.stdin.write("exit\n")
                self.child.stdin.flush()
                self.child.wait(timeout=5)
            except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                self.child.kill()
                self.child.wait(timeout=5)
        if self.child.stdin:
            self.child.stdin.close()
        self.thread.join(timeout=2)
        if self.child.stderr:
            self.child.stderr.close()
        if self.child.stdout:
            self.child.stdout.close()

    def test_real_registry_reads_and_changes_from_owned_child(self):
        self.assertEqual(self.metadata["provenance"], "owned_synthetic_child_not_bloodstrike")
        self.assertNotEqual(self.child.pid, os.getpid())
        first = collect_registry(self.reader, self.module)
        self.assertEqual(first.records[0].position.position, (101.25, -202.5, 303.75))
        self.child.stdin.write("mutate\n")
        self.child.stdin.flush()
        self.assertEqual(self.lines.get(timeout=5).strip(), "mutated")
        second = collect_registry(self.reader, self.module)
        self.assertEqual(second.records[0].position.position, (199.5, -202.5, 303.75))
        self.assertEqual(second.records[0].key, first.records[0].key)
        # Explicitly no assertion that equal addresses/keys imply a lifetime generation.

    def test_uncommitted_invalid_and_closed_reads_fail(self):
        with self.assertRaises(MemoryReadError):
            self.reader.read(self.module.base + 0x9000000, 8)
        with self.assertRaises(MemoryReadError):
            self.reader.read(1, 8)
        self.reader.close()
        with self.assertRaisesRegex(MemoryReadError, "closed"):
            self.reader.read(self.metadata["addresses"]["root"], 8)
        self.reader.close()  # Idempotent, no double close.

    def test_full_path_module_selection_for_the_owned_interpreter(self):
        path = self.reader.image_path
        self.assertEqual(os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(sys.executable)))
        module = find_module(self.child.pid, path)
        self.assertGreater(module.base, 0x10000)
        self.assertGreater(module.size, 0)

    def test_close_waits_for_an_inflight_native_read(self):
        entered, release, closing, closed = (threading.Event() for _ in range(4))
        original = self.reader._api
        errors, output = [], []
        class BlockingApi:
            def ReadProcessMemory(self, *args):
                entered.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("fixture gate was not released")
                return original.ReadProcessMemory(*args)
            def CloseHandle(self, handle):
                return original.CloseHandle(handle)
        self.reader._api = BlockingApi()
        def read():
            try:
                output.append(self.reader.read(self.metadata["addresses"]["root"] + 8, 8))
            except BaseException as exc:
                errors.append(exc)
        def close():
            closing.set()
            try:
                self.reader.close()
            except BaseException as exc:
                errors.append(exc)
            finally:
                closed.set()
        reading_thread = threading.Thread(target=read)
        closing_thread = threading.Thread(target=close)
        reading_thread.start()
        try:
            self.assertTrue(entered.wait(timeout=5))
            closing_thread.start()
            self.assertTrue(closing.wait(timeout=5))
            self.assertFalse(closed.wait(timeout=0.1), "close ran while a read owned the handle")
        finally:
            release.set()
            reading_thread.join(timeout=5)
            if closing_thread.ident:
                closing_thread.join(timeout=5)
        self.assertFalse(errors)
        self.assertEqual(int.from_bytes(output[0], "little"), self.metadata["addresses"]["sentinel"])
        self.assertTrue(closed.is_set())


if __name__ == "__main__":
    unittest.main()
