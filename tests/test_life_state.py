# Python | tests/test_life_state.py | Python 3.12+ unittest | schema, interpreter and effective combat-state gates.
import unittest

from ExternalCore.life_state import COMBAT_STATES,state_context,life_state
from ExternalCore.python_owner import DataReader,PythonLayoutError
from ExternalCore.python_runtime import local_player
from ExternalCore.pipeline import process_frame
from test_python_dispatch import DispatchFixture


class LifeFixture(DispatchFixture):
    def setup_life(self):
        self.setup_context()
        self.type(self.module.base+0x7A15170,'type',{},dict_offset=0)
        self.set(self.module.base+0x7A15170+0x90,'<Q',self.module.base+0x2A1DB20)
        attrs={name:self.integer(value) for name,value in COMBAT_STATES.items()}
        attrs['__module__']=self.ascii('gshare.consts')
        self.enum=self.new_type('CombatState',attrs)
        dictionary=self.dictionary({'__name__':self.ascii('gshare.consts'),'CombatState':self.enum})
        self.consts=self.alloc(56,[(0,'<3Q',[1,self.module.base+0x7A1B1F0,dictionary])])
        modules=self.data().dictionary(self.modules);modules['gshare.consts']=self.consts
        self.set(self.interpreter+0x1DE8,'<Q',self.dictionary(modules))
        return self
    def set_state(self,value):
        self.set(self.a['host']+0x10,'<Q',self.dictionary({'faction':self.integer(1),
            'combat_state':self.integer(value),'model':self.a['instance']}))
    def life(self):
        data=self.data();context,_,_=local_player(data)
        return life_state(data,state_context(data,context),self.a['host'])


class LifeStateTests(unittest.TestCase):
    def test_all_six_states_use_the_verified_schema_and_not_hp(self):
        f=LifeFixture().setup_life()
        for name,value in COMBAT_STATES.items():
            f.set_state(value);state=f.life()
            with self.subTest(name=name):
                self.assertEqual(state.name,name)
                self.assertIs(state.alive,name=='ALIVE')
                self.assertEqual(state.source,'instance')

    def test_unknown_state_and_changed_enum_integer_remain_unknown(self):
        f=LifeFixture().setup_life();f.set_state(7)
        with self.assertRaisesRegex(PythonLayoutError,'outside'):f.life()
        attrs={name:f.integer(value) for name,value in COMBAT_STATES.items()}
        attrs.update(ALIVE=f.integer(7),__module__=f.ascii('gshare.consts'))
        f.set(f.enum+0x108,'<Q',f.dictionary(attrs))
        with self.assertRaisesRegex(PythonLayoutError,'pinned integer schema'):f.life()

    def test_native_state_can_be_read_only_after_effective_getter_and_alias_checks(self):
        f=LifeFixture().setup_life().native_properties({'combat_state':('int',0),'server_hp':('float',0.0)})
        state=f.life()
        self.assertIs(state.alive,True);self.assertEqual(state.source,'native_numeric')
        f.set(f.a['native_bridge']+0x20,'<Q',f.a['owner'])
        with self.assertRaisesRegex(PythonLayoutError,'cached map'):f.life()

    def test_pipeline_exposes_state_name_and_keeps_visibility_unknown(self):
        f=LifeFixture().setup_life();f.set_state(0)
        state=process_frame(f.memory(),f.module).scene.actors[0].classification
        self.assertIs(state.alive,True)
        self.assertIsNone(state.visible)
        self.assertEqual(state.facts.life_state_name,'ALIVE')
        f.set_state(1)
        state=process_frame(f.memory(),f.module).scene.actors[0].classification
        self.assertIs(state.alive,False)
        self.assertEqual(state.facts.life_state_name,'DYING')

    def test_metaclass_hook_or_shadow_cannot_be_bypassed_by_enum_dictionary(self):
        for fault in ['hook','shadow']:
            f=LifeFixture().setup_life();f.set_state(0)
            if fault=='hook':f.set(f.module.base+0x7A15170+0x90,'<Q',f.module.base+0x123456)
            else:f.set(f.module.base+0x7A15170+0x108,'<Q',f.dictionary({'ALIVE':f.integer(3)}))
            with self.subTest(fault=fault),self.assertRaises(PythonLayoutError):f.life()


if __name__=='__main__':unittest.main()
