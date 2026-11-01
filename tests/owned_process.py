# Python | tests/owned_process.py | Python 3.12+ / Windows | lifecycle of an explicitly created fixture child.
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading

from ExternalCore.build import ModuleIdentity
from ExternalCore.entity_position import SAMPLE_SHA256
from ExternalCore.win32_memory import WindowsProcessMemory


class OwnedProcess:
    def __init__(self):
        self.reader = None
        self.child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("native_fixture.py"))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.lines = queue.Queue()
        def consume():
            for line in self.child.stdout:
                self.lines.put(line)
        self.thread = threading.Thread(target=consume, daemon=True)
        self.thread.start()
        try:
            self.metadata = json.loads(self.lines.get(timeout=15))
            if self.metadata["pid"] != self.child.pid or self.metadata["provenance"] != "owned_synthetic_child_not_bloodstrike":
                raise ValueError("fixture child identity/provenance mismatch")
            self.module = ModuleIdentity(self.metadata["base"], 0x94E9000, SAMPLE_SHA256)
            self.reader = WindowsProcessMemory(self.child.pid)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.reader:
            self.reader.close()
        if self.child.poll() is None:
            try:
                self.child.stdin.write("exit\n"); self.child.stdin.flush()
                self.child.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.child.kill(); self.child.wait(timeout=5)
        self.thread.join(timeout=2)
        for pipe in (self.child.stdin, self.child.stdout, self.child.stderr):
            pipe.close()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
