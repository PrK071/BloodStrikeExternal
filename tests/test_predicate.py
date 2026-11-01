# Python | tests/test_predicate.py | Python 3.12+ unittest | data-only predicate identity and impostor cases.
import struct
import unittest

from ExternalCore.memory import MemoryReadError
from ExternalCore.predicate import (base_is_enemy_body,bytes_value,canonical_wordcode,
    canonical_hash,tuple_objects,inspect_base_is_enemy)
from ExternalCore.predicate_spec import BASE_IS_ENEMY
from ExternalCore.python_owner import DataReader,PythonLayoutError
from state_fixture import StateFixture


class PredicateFixture(StateFixture):
    def bytes(self,value):
        return self.alloc(33+len(value),[(0,'<QQqQ',[1,self.module.base+0x7A16100,len(value),0]),
            (32,f'<{len(value)+1}s',[value+b'\0'])])
    def predicate(self):
        self.names=self.mro([self.ascii('faction')])
        self.constants=self.mro([self.module.base+0x7A12990,self.module.base+0x7A129B0])
        self.locals=self.mro([self.ascii(name) for name in ['self','a','b']])
        self.kinds=self.bytes(bytes.fromhex('26 26 26'))
        self.exceptions=self.bytes(b'')
        raw=bytes.fromhex(BASE_IS_ENEMY['code_hex'])
        self.code=self.alloc(0xD0+len(raw),[
            (0,'<QQq',[1,self.module.base+0x7A28410,len(raw)//2]),
            (0x18,'<3Q',[self.constants,self.names,self.exceptions]),
            (0x30,'<5i',[134217731,3,0,0,2]),(0x48,'<i',[3]),(0x50,'<3i',[3,0,0]),
            (0x60,'<2Q',[self.locals,self.kinds]),
            (0x70,'<3Q',[self.ascii('gshare/game_logic/igame_logic_base.py'),self.ascii('IsEnemy'),
                         self.ascii('IGameLogicBase.IsEnemy')]),
            (0xD0,f'<{len(raw)}s',[raw])])
        self.function=self.alloc(0x98,[(0,'<2Q',[1,self.module.base+0x7A135A0]),(0x30,'<Q',[self.code])])
        return self
    def body(self):return base_is_enemy_body(DataReader(self.memory(),self.module),self.function)


class PredicateTests(unittest.TestCase):
    def test_original_body_matches_but_does_not_certify_dispatch_or_operand_getters(self):
        f=PredicateFixture().predicate();body=f.body()
        self.assertEqual(body.canonical_sha256,'b632457e07b643ddb05ff3b4de958097174ce648941cd15075b3b9f6831f20c5')
        self.assertEqual((body.function,body.code),(f.function,f.code))
        self.assertIs(body.active_dispatch_verified,False)
        self.assertIs(body.operand_semantics_verified,False)

    def test_specializations_and_mutable_caches_preserve_semantic_identity(self):
        f=PredicateFixture().predicate()
        original=bytes.fromhex(BASE_IS_ENEMY['code_hex']);altered=bytearray(original)
        deopt=bytes.fromhex(BASE_IS_ENEMY['deopt_hex']);caches=bytes.fromhex(BASE_IS_ENEMY['caches_hex'])
        substitutions=0
        for offset,base,arg in BASE_IS_ENEMY['canonical']:
            alternatives=[op for op in BASE_IS_ENEMY['valid_opcodes'] if 0<op<234 and op!=base and deopt[op]==base]
            if alternatives:altered[offset]=min(alternatives);substitutions+=1
            altered[offset+2:offset+2*(1+caches[base])]=b'\xA5'*(2*caches[base])
        self.assertEqual(substitutions,13)
        before=DataReader(f.memory(),f.module);first=base_is_enemy_body(before,f.function)
        f.set(f.code+0xD0,f'<{len(altered)}s',bytes(altered))
        after=DataReader(f.memory(),f.module);second=base_is_enemy_body(after,f.function)
        self.assertEqual(first,second)
        self.assertEqual(before.trace,after.trace)
        self.assertEqual(canonical_hash(canonical_wordcode(original)),first.canonical_sha256)

    def test_name_and_code_labels_cannot_hide_changed_semantic_inputs(self):
        for fault in ['attribute','constant','local','kinds','exception','opcode','argcount','flags','freevar']:
            f=PredicateFixture().predicate()
            if fault=='attribute':f.set(f.names+32,'<Q',f.ascii('team_id'))
            elif fault=='constant':f.set(f.constants+32,'<Q',f.module.base+0x7A129B0)
            elif fault=='local':f.set(f.locals+40,'<Q',f.ascii('other'))
            elif fault=='kinds':f.set(f.kinds+32,'<B',0x20)
            elif fault=='exception':f.set(f.code+0x28,'<Q',f.bytes(b'\x01'))
            elif fault=='opcode':f.set(f.code+0xD0+2,'<B',86)
            elif fault=='argcount':f.set(f.code+0x34,'<i',2)
            elif fault=='flags':f.set(f.code+0x30,'<i',3)
            else:f.set(f.code+0x58,'<i',1)
            with self.subTest(fault=fault),self.assertRaises(PythonLayoutError):f.body()

    def test_types_defaults_closure_and_instrumentation_are_not_guessed(self):
        for fault in ['function_type','code_type','default','kwdefault','closure','executor','monitor','code_size']:
            f=PredicateFixture().predicate()
            if fault=='function_type':f.set(f.function+8,'<Q',f.module.base+0x7A28410)
            elif fault=='code_type':f.set(f.code+8,'<Q',f.module.base+0x7A135A0)
            elif fault in ['default','kwdefault','closure']:
                f.set(f.function+{'default':0x38,'kwdefault':0x40,'closure':0x48}[fault],'<Q',f.mro([]))
            elif fault in ['executor','monitor']:f.set(f.code+{'executor':0x98,'monitor':0xB0}[fault],'<Q',0x200001000)
            else:f.set(f.code+0x10,'<q',-1)
            with self.subTest(fault=fault),self.assertRaises(PythonLayoutError):f.body()

    def test_unsupported_opcodes_cache_overrun_and_extended_arg_bounds(self):
        for raw in [b'',b'\x80',b'\x00\x00',b'\xD3\x00',b'\xEA\x00',b'\xFF\x00',
                    b'\x50\x00',b'\x45\x01',b'\x45\x01'*4+b'\x56\x00']:
            with self.subTest(raw=raw.hex()),self.assertRaises(PythonLayoutError):canonical_wordcode(raw)
        self.assertEqual(canonical_wordcode(b'\x45\x01\x56\x02'),((0,69,1),(2,86,258)))

    def test_empty_and_repeated_semantic_tuple_items_are_distinct_from_mro_rules(self):
        f=PredicateFixture();empty=f.mro([]);repeated=f.mro([f.module.base+0x7A12990]*2)
        data=DataReader(f.memory(),f.module)
        self.assertEqual(tuple_objects(data,empty),())
        self.assertEqual(tuple_objects(data,repeated),(f.module.base+0x7A12990,)*2)
        with self.assertRaises(PythonLayoutError):tuple_objects(data,repeated,maximum=1)

    def test_bytes_size_terminator_and_exact_type_are_checked(self):
        for fault in ['negative','large','terminator','type','missing']:
            f=PredicateFixture();address=f.bytes(b'abc')
            if fault=='negative':f.set(address+16,'<q',-1)
            elif fault=='large':f.set(address+16,'<q',65537)
            elif fault=='terminator':f.set(address+35,'<B',1)
            elif fault=='type':f.set(address+8,'<Q',f.module.base+0x7A16E10)
            else:address+=0x1000
            with self.subTest(fault=fault),self.assertRaises((PythonLayoutError,MemoryReadError)):
                bytes_value(DataReader(f.memory(),f.module),address)

    def test_independent_reads_reject_changed_code_pointer_even_for_equal_bodies(self):
        f=PredicateFixture().predicate();original=f.memory().read(f.code,0xD0+174)
        replacement=f.alloc(len(original),[(0,f'<{len(original)}s',[original])])
        class MutatingReader:
            count=0
            def read(self,address,size):
                if address==f.function+8:
                    self.count+=1
                    if self.count==2:f.set(f.function+0x30,'<Q',replacement)
                return f.memory().read(address,size)
        with self.assertRaisesRegex(PythonLayoutError,'changed between'):
            inspect_base_is_enemy(MutatingReader(),f.module,f.function)


if __name__=='__main__':unittest.main()
