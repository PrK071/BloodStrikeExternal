# Python | tests/test_km_core_client.py | unittest | no driver, no elevation
"""Unit tests for tools/km_core_client.py using a fake DeviceIoControl.

Nothing here opens a device or talks to a kernel driver. The fake transport
exercises the client's *validation* logic (header construction, reply size,
struct size, ABI version, error mapping); it does not claim that any kernel
operation succeeded, and it does not invent features the client does not have.
"""
import ctypes
from ctypes import wintypes
import importlib.util
import io
from pathlib import Path
import struct
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / "tools" / "km_core_client.py"


def _load_client():
    spec = importlib.util.spec_from_file_location("km_core_client_under_test", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)          # runs _check_layout()
    return module


kc = _load_client()

ABSENT_DEVICE = r"\\.\KmCoreAbsentForUnitTests"


class FakeKernel32:
    """Minimal stand-in for kernel32.DeviceIoControl.

    The handler receives the KM_QUERY instance sent by the client, the response
    instance to fill, and the caller's DWORD for the returned byte count.
    """

    def __init__(self, handler):
        self.handler = handler
        self.calls = []
        self.closed = None

    def CloseHandle(self, handle):
        self.closed = handle
        return 1

    def DeviceIoControl(self, handle, code, in_ref, in_len,
                        out_ref, out_len, returned_ref, overlapped):
        query = in_ref._obj
        response = out_ref._obj
        self.calls.append({
            "handle": handle,
            "code": code,
            "in_len": in_len,
            "out_len": out_len,
            "abi": query.AbiVersion,
            "struct_size": query.StructSize,
            "command": query.Command,
            "reserved": query.Reserved,
        })
        return self.handler(query, response, returned_ref._obj)


def make_client(handler):
    """Build a KmCore without running __init__ (which would open a device)."""
    fake = FakeKernel32(handler)
    device = kc.KmCore.__new__(kc.KmCore)
    device.pid = 4242
    device._path = "<fake>"
    device._handle = 1
    device._k32 = fake
    return device, fake


def reply_version(query, response, returned):
    response.AbiVersion = 1
    response.StructSize = ctypes.sizeof(response)
    response.DriverVersion = 0x00010000
    response.BuildNumber = 7
    returned.value = ctypes.sizeof(response)
    return 1


def reply_state(query, response, returned):
    response.State = 1
    response.UptimeSeconds = 42
    response.RequestsServed = 99
    returned.value = ctypes.sizeof(response)
    return 1


def reply_caps(query, response, returned):
    response.StructSize = ctypes.sizeof(response)
    response.CapabilityMask = 0x7
    response.MaxRequest = 0
    response.Reserved = 0
    returned.value = ctypes.sizeof(response)
    return 1


def dispatch_all(query, response, returned):
    """Route by the Command echo, the same way the kernel switch does."""
    if query.Command == kc.IOCTL_KM_GET_VERSION:
        return reply_version(query, response, returned)
    if query.Command == kc.IOCTL_KM_GET_STATE:
        return reply_state(query, response, returned)
    if query.Command == kc.IOCTL_KM_GET_CAPS:
        return reply_caps(query, response, returned)
    ctypes.set_last_error(1)               # ERROR_INVALID_FUNCTION
    return 0


class TestConstants(unittest.TestCase):
    def test_ioctl_codes(self):
        self.assertEqual(kc.IOCTL_KM_GET_VERSION, 0x226000)
        self.assertEqual(kc.IOCTL_KM_GET_STATE, 0x226004)
        self.assertEqual(kc.IOCTL_KM_GET_CAPS, 0x226008)

    def test_ctl_code_formula(self):
        # CTL_CODE(0x22, 0x801, METHOD_BUFFERED, FILE_READ_DATA) recomputed
        expected = (0x22 << 16) | (0x1 << 14) | (0x801 << 2) | 0
        self.assertEqual(kc.IOCTL_KM_GET_STATE, expected)

    def test_abi_version(self):
        self.assertEqual(kc.ABI_VERSION, 1)


class TestLayout(unittest.TestCase):
    def test_sizes_and_alignment(self):
        for struct_type in (kc.KM_QUERY, kc.KM_VERSION, kc.KM_STATE, kc.KM_CAPS):
            self.assertEqual(ctypes.sizeof(struct_type), 0x10, struct_type.__name__)
        self.assertEqual(ctypes.alignment(kc.KM_QUERY), 4)
        self.assertEqual(ctypes.alignment(kc.KM_STATE), 8)

    def test_field_offsets(self):
        self.assertEqual(kc.KM_QUERY.Command.offset, 0x08)
        self.assertEqual(kc.KM_STATE.RequestsServed.offset, 0x08)
        self.assertEqual(kc.KM_CAPS.CapabilityMask.offset, 0x04)
        self.assertEqual(kc.KM_VERSION.BuildNumber.offset, 0x0C)

    def test_field_order(self):
        self.assertEqual([n for n, _ in kc.KM_QUERY._fields_],
                         ["AbiVersion", "StructSize", "Command", "Reserved"])
        self.assertEqual([n for n, _ in kc.KM_STATE._fields_],
                         ["State", "UptimeSeconds", "RequestsServed"])


class TestSerialization(unittest.TestCase):
    def test_query_wire_format(self):
        raw = bytes(kc.KM_QUERY(1, 0x10, 0x226000, 0))
        self.assertEqual(raw, struct.pack("<IIII", 1, 0x10, 0x226000, 0))
        self.assertEqual(len(raw), 0x10)

    def test_state_wire_format(self):
        raw = bytes(kc.KM_STATE(1, 42, 99))
        self.assertEqual(raw, struct.pack("<IIQ", 1, 42, 99))


class TestRequestHeader(unittest.TestCase):
    def test_header_sent_for_version(self):
        device, fake = make_client(reply_version)
        device.get_version()
        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["code"], kc.IOCTL_KM_GET_VERSION)
        self.assertEqual(call["in_len"], 0x10)
        self.assertEqual(call["out_len"], 0x10)
        self.assertEqual(call["abi"], 1)
        self.assertEqual(call["struct_size"], 0x10)
        self.assertEqual(call["command"], kc.IOCTL_KM_GET_VERSION)
        self.assertEqual(call["reserved"], 0)
        self.assertEqual(call["handle"], 1)


class TestSuccessfulReplies(unittest.TestCase):
    def test_version(self):
        device, _ = make_client(reply_version)
        version = device.get_version()
        self.assertEqual(version.AbiVersion, 1)
        self.assertEqual(version.DriverVersion, 0x00010000)
        self.assertEqual(version.BuildNumber, 7)

    def test_state(self):
        """KM_STATE has no StructSize; get_state() must work anyway (0006)."""
        device, _ = make_client(reply_state)
        state = device.get_state()
        self.assertEqual(state.State, 1)
        self.assertEqual(state.UptimeSeconds, 42)
        self.assertEqual(state.RequestsServed, 99)

    def test_caps(self):
        device, _ = make_client(reply_caps)
        caps = device.get_caps()
        self.assertEqual(caps.CapabilityMask, 0x7)
        self.assertEqual(caps.MaxRequest, 0)

    def test_format_version(self):
        self.assertEqual(kc._format_version(0x00010000), "1.0")
        self.assertEqual(kc._format_version(0x00020007), "2.7")

    def test_unknown_state_value_is_not_invented(self):
        # the client passes values through; it must not fabricate a name
        self.assertEqual(sorted(kc.STATE_NAMES), [0, 1, 2])
        self.assertNotIn(99, kc.STATE_NAMES)


class TestReplyValidation(unittest.TestCase):
    def test_short_reply_rejected(self):
        def handler(query, response, returned):
            response.AbiVersion = 1
            response.StructSize = ctypes.sizeof(response)
            returned.value = 8              # fewer bytes than the struct
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_version()

    def test_oversized_reply_rejected(self):
        def handler(query, response, returned):
            response.AbiVersion = 1
            response.StructSize = ctypes.sizeof(response)
            returned.value = 0x20           # more bytes than the struct
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_version()

    def test_wrong_struct_size_rejected(self):
        def handler(query, response, returned):
            response.AbiVersion = 1
            response.StructSize = 0x08      # driver disagrees about its own ABI
            returned.value = ctypes.sizeof(response)
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_version()

    def test_abi_mismatch_in_reply_rejected(self):
        def handler(query, response, returned):
            response.AbiVersion = 2         # newer/older ABI than this client
            response.StructSize = ctypes.sizeof(response)
            returned.value = ctypes.sizeof(response)
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_version()


class TestStructSizeContract(unittest.TestCase):
    """Proposal 0006: KM_STATE has no StructSize; KM_VERSION/KM_CAPS do."""

    def test_state_works_without_struct_size_field(self):
        self.assertNotIn("StructSize", [n for n, _ in kc.KM_STATE._fields_])
        self.assertFalse(hasattr(kc.KM_STATE(), "StructSize"))
        device, _ = make_client(reply_state)
        state = device.get_state()
        self.assertEqual((state.State, state.UptimeSeconds, state.RequestsServed),
                         (1, 42, 99))

    def test_version_rejects_wrong_struct_size(self):
        def handler(query, response, returned):
            response.AbiVersion = 1
            response.StructSize = 0x0C      # KM_VERSION is 0x10
            response.DriverVersion = 0x00010000
            response.BuildNumber = 1
            returned.value = ctypes.sizeof(response)
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_version()

    def test_caps_rejects_wrong_struct_size(self):
        def handler(query, response, returned):
            response.StructSize = 0x08      # KM_CAPS is 0x10
            response.CapabilityMask = 0x7
            response.MaxRequest = 0
            returned.value = ctypes.sizeof(response)
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_caps()

    def test_state_still_rejects_wrong_returned_size(self):
        # KM_STATE no longer has a StructSize check, so the byte count is the
        # remaining guard for that reply and must keep working.
        def handler(query, response, returned):
            response.State = 1
            response.UptimeSeconds = 1
            response.RequestsServed = 1
            returned.value = 8              # KM_STATE is 0x10
            return 1

        device, _ = make_client(handler)
        with self.assertRaises(kc.KmCoreError):
            device.get_state()


class TestCliSession(unittest.TestCase):
    def test_full_session_with_fake_transport(self):
        """A complete run of main(): version, state and caps, real printing."""
        out, err = io.StringIO(), io.StringIO()
        original_init = kc.KmCore.__init__

        def fake_init(self, path=kc.DEVICE_PATH):
            self._path = path
            self._handle = 1
            self._k32 = FakeKernel32(dispatch_all)
            self.pid = 4242

        try:
            kc.KmCore.__init__ = fake_init
            with redirect_stdout(out), redirect_stderr(err):
                code = kc.main([kc.DEVICE_PATH])
        finally:
            kc.KmCore.__init__ = original_init

        text = out.getvalue()
        self.assertEqual(code, 0, msg=err.getvalue())
        for needle in ("driver   : 1.0 build 7",
                       "abi      : 1",
                       "state    : ready (42s uptime, 99 requests)",
                       "caps     : get_version, get_state, get_caps",
                       "max xfer : 0 bytes"):
            self.assertIn(needle, text)


class TestTransportErrors(unittest.TestCase):
    def test_transport_failure_maps_to_oserror(self):
        def handler(query, response, returned):
            ctypes.set_last_error(5)        # ERROR_ACCESS_DENIED
            return 0

        device, _ = make_client(handler)
        with self.assertRaises(OSError) as ctx:
            device.get_version()
        self.assertEqual(getattr(ctx.exception, "winerror", None), 5)

    def test_open_absent_device_raises(self):
        with self.assertRaises(OSError):
            kc.KmCore(ABSENT_DEVICE)

    def test_main_without_device_returns_1(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = kc.main([ABSENT_DEVICE])
        self.assertEqual(code, 1)
        self.assertIn("WinError", err.getvalue())


class TestSurface(unittest.TestCase):
    def test_public_surface_has_no_memory_operations(self):
        public = {n for n in dir(kc.KmCore) if not n.startswith("_")}
        self.assertEqual(public, {"get_version", "get_state", "get_caps", "close"})

    def test_no_read_write_helpers(self):
        for name in ("read", "write", "read_process", "write_process", "image_path"):
            self.assertFalse(hasattr(kc.KmCore, name), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
