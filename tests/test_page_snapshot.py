# Python | tests/test_page_snapshot.py | Python 3.12+ unittest | pass-scoped pages, no cross-pass lifetime cache.
import unittest

from ExternalCore.memory import PageSnapshotReader,MemoryReadError


class PageSnapshotTests(unittest.TestCase):
    def test_small_reads_share_one_page_only_within_the_same_pass(self):
        class Memory:
            def __init__(self):self.raw=bytearray(b'a'*8192);self.calls=[]
            def read(self,address,size):
                self.calls.append((address,size))
                return bytes(self.raw[address-0x10000:address-0x10000+size])
        memory=Memory();one=PageSnapshotReader(memory)
        self.assertEqual(one.read(0x10008,4),b'aaaa')
        memory.raw[8:12]=b'new!'
        self.assertEqual(one.read(0x10008,4),b'aaaa')
        self.assertEqual(len(memory.calls),1)
        self.assertEqual(PageSnapshotReader(memory).read(0x10008,4),b'new!')
        self.assertEqual(len(memory.calls),2)

    def test_page_boundary_partial_reads_and_budget_have_no_partial_success(self):
        class Memory:
            def read(self,address,size):
                if address>=0x11000:raise MemoryReadError('unmapped second page')
                return b'x'*size
        data=PageSnapshotReader(Memory(),max_pages=1)
        self.assertEqual(data.read(0x10FF8,8),b'x'*8)
        with self.assertRaises(MemoryReadError):data.read(0x10FF8,16)
        self.assertEqual(len(data.pages),1)


if __name__=='__main__':unittest.main()
