# Python | tests/test_python_values.py | Python 3.12+ unittest | independent pinned-ABI scalar buffers.
import math
import struct
import unittest

from ExternalCore.build import ModuleIdentity
from ExternalCore.entity_position import SAMPLE_SHA256
from ExternalCore.memory import Segment, SnapshotMemory
from ExternalCore.python_owner import DataReader, PythonLayoutError, TRUE, FALSE, NONE
from ExternalCore.python_values import read_scalar

BASE, OBJECT = 0x180000000, 0x200000000
MODULE = ModuleIdentity(BASE,0x94E9000,SAMPLE_SHA256)


def reader(raw):
    return DataReader(SnapshotMemory([Segment(OBJECT,bytes(raw))]),MODULE)


def long_raw(value, *, small_flag=False):
    magnitude, words = abs(value), []
    while magnitude:
        words.append(magnitude & ((1<<30)-1))
        magnitude >>= 30
    raw = bytearray(24+4*max(1,len(words)))
    sign = 1 if value == 0 else (2 if value < 0 else 0)
    struct.pack_into("<QQQ",raw,0,1,BASE+0x7A18530,(len(words)<<3)|sign|(4 if small_flag else 0))
    if words:
        struct.pack_into(f"<{len(words)}I",raw,24,*words)
    else:
        struct.pack_into("<I",raw,24,0xDEADBEEF)  # Undefined storage must not affect zero.
    return raw


class PythonScalarTests(unittest.TestCase):
    def test_bool_singletons_are_not_silently_decoded_as_integer_team_ids(self):
        data = DataReader(SnapshotMemory([]),MODULE)
        for rva,expected in [(TRUE,True),(FALSE,False)]:
            scalar = read_scalar(data,BASE+rva)
            self.assertEqual(scalar.kind,"bool")
            self.assertIs(scalar.value,expected)
        scalar=read_scalar(data,BASE+NONE)
        self.assertEqual(scalar.kind,'none')
        self.assertIsNone(scalar.value)

    def test_zero_signed_single_and_multi_digit_integers(self):
        for value in [0,1,-1,2**30-1,2**30,-2**63,2**64-1,2**127-1]:
            for flag in [False,True] if abs(value)<256 else [False]:
                with self.subTest(value=value,small_flag=flag):
                    scalar = read_scalar(reader(long_raw(value,small_flag=flag)),OBJECT)
                    self.assertEqual(scalar.kind,"int")
                    self.assertEqual(scalar.value,value)

    def test_integer_bounds_and_malformed_representation_fail(self):
        malformed = []
        tag = long_raw(1);struct.pack_into("<Q",tag,16,11);malformed.append(tag) # sign3
        digit = long_raw(1);struct.pack_into("<I",digit,24,1<<30);malformed.append(digit)
        leading = long_raw(2**30);struct.pack_into("<I",leading,28,0);malformed.append(leading)
        for raw in malformed:
            with self.subTest(),self.assertRaises(PythonLayoutError):read_scalar(reader(raw),OBJECT)
        with self.assertRaisesRegex(PythonLayoutError,"bit budget"):
            read_scalar(reader(long_raw(2**128)),OBJECT)

    def test_floats_preserve_double_precision_and_reject_nonfinite(self):
        for value in [0.0,-0.0,0.1,16777217.0,-1e100,math.nan,math.inf]:
            raw = struct.pack("<QQd",1,BASE+0x7A12E10,value)
            if math.isfinite(value):
                scalar = read_scalar(reader(raw),OBJECT)
                self.assertEqual(scalar.value,value)
                self.assertEqual(math.copysign(1,scalar.value),math.copysign(1,value))
            else:
                with self.assertRaises(PythonLayoutError):read_scalar(reader(raw),OBJECT)

    def test_ascii_scalar_limits_and_no_implicit_type_conversion(self):
        raw = bytearray(46)
        struct.pack_into("<QQq",raw,0,1,BASE+0x7A16E10,5)
        struct.pack_into("<I",raw,32,0x64);raw[40:]=b"alpha\0"
        self.assertEqual(read_scalar(reader(raw),OBJECT).value,"alpha")
        with self.assertRaises(PythonLayoutError):read_scalar(reader(raw),OBJECT,max_ascii_length=4)
        struct.pack_into("<Q",raw,8,BASE+0x1000)
        with self.assertRaisesRegex(PythonLayoutError,"conversion code"):
            read_scalar(reader(raw),OBJECT)


if __name__=="__main__":unittest.main()
