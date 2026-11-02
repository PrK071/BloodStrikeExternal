# Python | tests/test_python_dispatch.py | Python 3.12+ unittest | passive dispatch precedence and verified relation decisions.
import struct
import unittest

from ExternalCore.python_dispatch import (attribute,integer_attribute,passive_truth,enemy_context,
    evaluate_base_enemy,type_dictionary,GENERIC_GETATTRO,ENTITY_GETATTRO)
from ExternalCore.python_owner import DataReader,PythonLayoutError
from ExternalCore.python_runtime import local_player
from ExternalCore.memory import Segment
from ExternalCore.pipeline import process_frame
from ExternalCore.scene import Category
from test_predicate import PredicateFixture
from test_python_values import long_raw


class DispatchFixture(PredicateFixture):
    def integer(self,value):
        raw=long_raw(value)
        # long_raw's pinned module base agrees with this fixture's base.
        return self.alloc(len(raw),[(0,f'<{len(raw)}s',[bytes(raw)])])
    def new_type(self,name,attrs=None,bases=(),getter=GENERIC_GETATTRO):
        address=self.alloc(0x1A0)
        # StateFixture.type supplies the complete contiguous type metadata.
        self.segments=[s for s in self.segments if s.address!=address]
        self.type(address,name,attrs,bases)
        self.segments.append(Segment(address+352,bytes(0x1A0-352)))
        self.set(address+0x90,'<Q',self.module.base+getter)
        return address
    def new_object(self,cls,attrs):
        return self.alloc(40,[(0,'<QQQ',[1,cls,self.dictionary(attrs)])])
    def setup_context(self):
        self.predicate().runtime()
        logic_cls=self.new_type('GameLogic',{'IsEnemy':self.function})
        self.logic=self.new_object(logic_cls,{})
        space_cls=self.new_type('Space')
        self.space=self.new_object(space_cls,{'game_logic':self.logic})
        globals_=DataReader(self.memory(),self.module).dictionary(self.genv_dict)
        globals_['space']=self.space
        self.set(self.genv+0x10,'<Q',self.dictionary(globals_))
        self.host_cls=int.from_bytes(self.memory().read(self.a['host']+8,8),'little')
        self.set(self.host_cls+0x90,'<Q',self.module.base+GENERIC_GETATTRO)
        self.set(self.a['host']+0x10,'<Q',self.dictionary({'faction':self.integer(1),'model':self.a['instance']}))
        self.target=self.new_object(self.host_cls,{'faction':self.integer(2)})
        return self
    def data(self):return DataReader(self.memory(),self.module)
    def context(self,data):
        module,host,area=local_player(data)
        return enemy_context(data,module)
    def native_properties(self,values=None):
        self.properties({'faction':('int',1)} if values is None else values)
        backing=int.from_bytes(self.memory().read(self.a['prop']+0x20,8),'little')
        bridge=self.alloc(40,[(0,'<Q',[self.a['host']]),(0x10,'<3Q',[self.a['owner'],self.a['prop'],backing])])
        self.set(self.a['host']+0x20,'<Q',bridge)
        self.set(self.a['native_area']+0x38,'<Q',bridge)
        cls=int.from_bytes(self.memory().read(self.a['host']+8,8),'little')
        self.set(cls+0x90,'<Q',self.module.base+ENTITY_GETATTRO)
        self.set(self.a['host']+0x10,'<Q',self.dictionary({}))
        self.a['native_bridge']=bridge
        return self
    def choose_other_local(self):
        area_cls=int.from_bytes(self.memory().read(self.a['owner']+8,8),'little')
        native=self.alloc(0x1E0);area_bridge=self.alloc(16,[(0,'<Q',[native])])
        area=self.alloc(40,[(0,'<2Q',[1,area_cls]),(0x20,'<Q',[area_bridge])])
        bridge=self.alloc(40,[(0,'<Q',[self.target]),(0x10,'<Q',[area])])
        self.set(native+0x38,'<Q',bridge);self.set(self.target+0x20,'<Q',bridge)
        globals_=self.data().dictionary(int.from_bytes(self.memory().read(self.genv+0x10,8),'little'))
        globals_['player']=globals_['main_player']=self.target
        self.set(self.genv+0x10,'<Q',self.dictionary(globals_))
        return self


class DispatchTests(unittest.TestCase):
    def test_selected_bound_body_and_exact_integer_operands_close_base_relation(self):
        f=DispatchFixture().setup_context();data=f.data();context=f.context(data)
        self.assertTrue(context.body.active_dispatch_verified)
        decision=evaluate_base_enemy(data,context,f.a['host'],f.target)
        self.assertEqual((decision.enemy,decision.local_faction,decision.target_faction),(True,1,2))
        self.assertEqual(decision.rule,'verified_base_faction_comparison')

    def test_identity_and_negative_faction_keep_original_short_circuit_order(self):
        f=DispatchFixture().setup_context()
        f.set(f.a['host']+0x10,'<Q',f.dictionary({'faction':f.integer(-1)}))
        f.set(f.target+0x10,'<Q',f.dictionary({}))
        data=f.data();context=f.context(data)
        self.assertFalse(evaluate_base_enemy(data,context,f.a['host'],f.a['host']).enemy)
        result=evaluate_base_enemy(data,context,f.a['host'],f.target)
        self.assertTrue(result.enemy);self.assertIsNone(result.target_faction)

    def test_instance_value_overrides_non_descriptor_class_attribute(self):
        f=DispatchFixture().setup_context()
        f.set(f.host_cls+0x108,'<Q',f.dictionary({'faction':f.integer(9)}))
        self.assertEqual(integer_attribute(f.data(),f.a['host'],'faction'),(1,'instance'))

    def test_data_descriptor_cannot_be_bypassed_by_an_instance_integer(self):
        f=DispatchFixture().setup_context();desc_cls=f.new_type('Descriptor')
        f.set(desc_cls+0x110,'<2Q',f.module.base+0x1000,f.module.base+0x2000)
        descriptor=f.new_object(desc_cls,{})
        f.set(f.host_cls+0x108,'<Q',f.dictionary({'faction':descriptor}))
        with self.assertRaisesRegex(PythonLayoutError,'data descriptor'):
            integer_attribute(f.data(),f.a['host'],'faction')

    def test_native_storage_requires_both_cached_aliases(self):
        for fault in [None,'map','backing']:
            f=DispatchFixture().native_properties()
            if fault:f.set(f.a['native_bridge']+{'map':0x18,'backing':0x20}[fault],'<Q',f.a['owner'])
            if fault:
                with self.subTest(fault=fault),self.assertRaisesRegex(PythonLayoutError,'cached map'):
                    integer_attribute(f.data(),f.a['host'],'faction')
            else:self.assertEqual(integer_attribute(f.data(),f.a['host'],'faction'),(1,'native_numeric'))

    def test_map_class_shadow_precedes_native_numeric_storage(self):
        f=DispatchFixture().native_properties()
        cls=int.from_bytes(f.memory().read(f.a['prop']+8,8),'little')
        f.set(cls+0x108,'<Q',f.dictionary({'faction':f.integer(42)}))
        self.assertEqual(integer_attribute(f.data(),f.a['host'],'faction'),(42,'class'))

    def test_custom_dispatch_and_truth_callbacks_are_unknown(self):
        f=DispatchFixture().setup_context()
        f.set(f.host_cls+0x90,'<Q',f.module.base+0x123456)
        with self.assertRaisesRegex(PythonLayoutError,'effective attribute hook'):
            integer_attribute(f.data(),f.a['host'],'faction')
        for offset,slot in [(0x60,0x48),(0x70,0),(0x68,0)]:
            f=DispatchFixture().setup_context()
            suite=f.alloc(80,[(slot,'<Q',[f.module.base+0x123456])]);f.set(f.host_cls+offset,'<Q',suite)
            with self.subTest(offset=offset),self.assertRaisesRegex(PythonLayoutError,'truth'):
                passive_truth(f.data(),f.a['host'])

    def test_instance_function_shadow_and_replaced_mode_body_are_rejected(self):
        for fault in ['shadow','body']:
            f=DispatchFixture().setup_context()
            if fault=='shadow':f.set(f.logic+0x10,'<Q',f.dictionary({'IsEnemy':f.function}))
            else:f.set(f.code+0x34,'<i',2)
            with self.subTest(fault=fault),self.assertRaises(PythonLayoutError):f.context(f.data())

    def test_bool_faction_and_unavailable_builtin_dictionary_are_not_guessed(self):
        f=DispatchFixture().setup_context()
        f.set(f.target+0x10,'<Q',f.dictionary({'faction':f.module.base+0x7A129B0}))
        with self.assertRaisesRegex(PythonLayoutError,'exact integer'):
            integer_attribute(f.data(),f.target,'faction')
        f.set(f.host_cls+0xA8,'<I',0x1002)
        with self.assertRaisesRegex(PythonLayoutError,'side-table'):
            attribute(f.data(),f.a['host'],'faction')

    def test_builtin_state_dictionary_uses_interpreter_type_identity_and_readiness(self):
        for secondary in [False,True]:
            f=DispatchFixture().setup_context()
            cls=f.new_type('StaticBuiltin')
            f.set(cls+0xA8,'<I',0x1002);f.set(cls+0x168,'<Q',1)
            dictionary=f.dictionary({'faction':f.integer(19)})
            raw=bytearray(48)
            struct.pack_into('<Q',raw,0,cls if not secondary else 0)
            struct.pack_into('<i',raw,0x10,1);struct.pack_into('<Q',raw,0x18,dictionary)
            f.segments.append(Segment(f.interpreter+0x2BF38,bytes(raw)))
            if secondary:
                struct.pack_into('<Q',raw,0,cls)
                f.segments.append(Segment(f.interpreter+0x2E4C8,bytes(raw)))
            data=f.data();data.interpreter=f.interpreter
            self.assertEqual(type_dictionary(data,cls)['faction'],
                             DataReader(f.memory(),f.module).dictionary(dictionary)['faction'])
            state=f.interpreter+(0x2E4C8 if secondary else 0x2BF38)
            f.set(state+0x10,'<i',0)
            data=f.data();data.interpreter=f.interpreter
            self.assertIn('faction',type_dictionary(data,cls))
            f.set(state+0xC,'<i',1)
            data=f.data();data.interpreter=f.interpreter
            with self.assertRaisesRegex(PythonLayoutError,'not ready'):type_dictionary(data,cls)

    def test_getattr_hook_accepts_only_the_pinned_getattribute_wrapper(self):
        for callback in [GENERIC_GETATTRO,0x123456]:
            f=DispatchFixture().setup_context()
            descriptor=f.alloc(56,[(0,'<2Q',[1,f.module.base+0x7A21E50]),
                (0x10,'<2Q',[f.host_cls,f.ascii('__getattribute__')]),
                (0x28,'<2Q',[f.module.base+0x7A13E60,f.module.base+callback])])
            f.set(f.host_cls+0x108,'<Q',f.dictionary({'__getattribute__':descriptor}))
            f.set(f.host_cls+0x90,'<Q',f.module.base+0x2A1DCA0)
            if callback==GENERIC_GETATTRO:
                self.assertEqual(integer_attribute(f.data(),f.a['host'],'faction'),(1,'instance'))
            else:
                with self.assertRaisesRegex(PythonLayoutError,'effective attribute hook'):
                    integer_attribute(f.data(),f.a['host'],'faction')

    def test_getattr_missing_generic_attribute_does_not_invoke_arbitrary_fallback(self):
        f=DispatchFixture().setup_context()
        descriptor=f.alloc(56,[(0,'<2Q',[1,f.module.base+0x7A21E50]),
            (0x10,'<2Q',[f.host_cls,f.ascii('__getattribute__')]),
            (0x28,'<2Q',[f.module.base+0x7A13E60,f.module.base+GENERIC_GETATTRO])])
        f.set(f.host_cls+0x108,'<Q',f.dictionary({'__getattribute__':descriptor,'__getattr__':f.function}))
        f.set(f.host_cls+0x90,'<Q',f.module.base+0x2A1DCA0)
        with self.assertRaisesRegex(PythonLayoutError,'absent'):
            integer_attribute(f.data(),f.a['host'],'combat_state')

    def test_pipeline_promotes_only_the_verified_relation_for_this_observation(self):
        f=DispatchFixture().setup_context().choose_other_local()
        frame=process_frame(f.memory(),f.module)
        state=frame.scene.actors[0].classification
        self.assertEqual(state.category,Category.OPPONENT)
        self.assertIs(state.local,False);self.assertIs(state.facts.relation,True)
        self.assertIsNone(state.alive);self.assertIsNone(frame.aim.target)
        # A custom hook prevents relation inference but retains the player model.
        f.set(f.host_cls+0x90,'<Q',f.module.base+0x123456)
        state=process_frame(f.memory(),f.module).scene.actors[0].classification
        self.assertEqual(state.category,Category.PLAYER)
        self.assertIsNone(state.facts.relation)


if __name__=='__main__':unittest.main()
