# Python | tests/test_runtime_state.py | Python 3.12+ unittest | native bridges, modules and typed property snapshots.
import unittest

from ExternalCore.aim import AimProfile
from ExternalCore.pipeline import process_frame
from ExternalCore.native_properties import NumericMap
from ExternalCore.python_owner import DataReader,PythonLayoutError
from ExternalCore.python_runtime import find_module,local_player
from ExternalCore.scene import Category
from state_fixture import StateFixture


class RuntimeStateTests(unittest.TestCase):
    def test_native_area_owner_bridge_and_local_module_context(self):
        f=StateFixture().runtime(extra_interpreter=True).properties()
        data=DataReader(f.memory(),f.module)
        context,player,area=local_player(data)
        self.assertEqual((context.interpreter_id,player,area),(0,f.a['host'],f.a['owner']))
        frame=process_frame(f.memory(),f.module,active=True,profile=AimProfile(counts_per_pixel=(1,1)))
        state=frame.scene.actors[0].classification
        self.assertIs(state.local,True)
        self.assertEqual(state.category,Category.PLAYER)
        self.assertIsNone(state.alive)  # HP100 is not a life-state proof.
        self.assertEqual({v.name:v.value for v in state.facts.values},
                         {'server_hp':100.0,'faction':1,'combat_state':7,'combat_team_id':3})
        self.assertIn('hp=100 local',frame.commands[2]['text'])

    def test_module_discovery_scans_bounded_large_name_tables(self):
        f=StateFixture().runtime(extra_modules=300)
        context=find_module(DataReader(f.memory(),f.module),'gclient.genv')
        self.assertEqual(context.module,f.genv)

    def test_interpreter_cycle_cookie_and_ambiguity_are_rejected(self):
        for fault in ['cycle','cookie','duplicate']:
            f=StateFixture().runtime()
            if fault=='cycle':f.set(f.interpreter+0x1C68,'<Q',f.interpreter)
            elif fault=='cookie':f.set(f.module.base+0x925F000,'<8s',b'wrongabi')
            else:
                second=f.alloc(0x1DF0,[(0x1C70,'<q',[1]),(0x1DE8,'<Q',[f.modules])])
                f.set(f.interpreter+0x1C68,'<Q',second)
            with self.subTest(fault=fault),self.assertRaises(PythonLayoutError):
                find_module(DataReader(f.memory(),f.module),'gclient.genv')

    def test_disagreeing_player_aliases_or_distinct_replay_do_not_guess_local(self):
        for kwargs in [dict(main=0x200077000),dict(replay=0x200077000)]:
            f=StateFixture().runtime(**kwargs)
            with self.subTest(kwargs=kwargs),self.assertRaises(PythonLayoutError):
                local_player(DataReader(f.memory(),f.module))
            frame=process_frame(f.memory(),f.module)
            self.assertIsNone(frame.scene.actors[0].classification.local)

    def test_typed_integer_float_and_mixed_numeric_values(self):
        for kind,values in [('int',{'faction':('int',-2**63)}),
                            ('float',{'server_hp':('float',0.1)}),
                            ('mixed',{'server_hp':('float',-0.0),'combat_state':('int',2**63-1)})]:
            f=StateFixture().properties(values,kind=kind)
            read=NumericMap(DataReader(f.memory(),f.module),f.a['owner']).read(values)
            self.assertEqual({name:entry.value for name,entry in read.items()},
                             {name:value for name,(value_kind,value) in values.items()})

    def test_unsupported_optional_property_preserves_supported_health(self):
        f=StateFixture().runtime().properties({'server_hp':('float',125.0),'combat_team_id':('int',3)})
        f.set(f.a['values']+16+8,'<B',2)
        frame=process_frame(f.memory(),f.module)
        state=frame.scene.actors[0].classification
        self.assertEqual({v.name:v.value for v in state.facts.values},{'server_hp':125.0})
        self.assertIn('combat_team_id',state.facts.diagnostics[0])

    def test_selected_dictionary_trace_ignores_unrequested_value_replacement(self):
        f=StateFixture()
        first_value=f.ascii('first')
        second_value=f.ascii('second')
        dictionary=f.dictionary({'model':f.a['instance'],'timer':first_value})
        keys=int.from_bytes(f.memory().read(dictionary+32,8),'little')
        before=DataReader(f.memory(),f.module)
        before.dictionary(dictionary,wanted={'model'})
        f.set(keys+40+16+8,'<Q',second_value)
        after=DataReader(f.memory(),f.module)
        after.dictionary(dictionary,wanted={'model'})
        self.assertEqual(before.trace,after.trace)
        f.set(keys+40+8,'<Q',f.a['owner'])
        changed=DataReader(f.memory(),f.module)
        changed.dictionary(dictionary,wanted={'model'})
        self.assertNotEqual(before.trace,changed.trace)

    def test_known_hash_lookup_handles_collisions_missing_keys_and_live_values(self):
        f=StateFixture()
        dictionary=f.dictionary({'model':f.a['instance'],'timer':f.a['owner']})
        keys=int.from_bytes(f.memory().read(dictionary+32,8),'little')
        first=int.from_bytes(f.memory().read(keys+40,8),'little')
        second=int.from_bytes(f.memory().read(keys+56,8),'little')
        f.set(first+24,'<q',3)
        f.set(second+24,'<q',11)
        f.set(keys+32,'<8b',1,-1,-1,0,-1,-1,-1,-1)
        hints={'model':3,'timer':11,'absent':19}
        data=DataReader(f.memory(),f.module,dictionary_hashes=hints)
        self.assertEqual(data.dictionary(dictionary,wanted=set(hints)),
                         {'model':f.a['instance'],'timer':f.a['owner']})
        f.set(keys+48,'<Q',f.a['host'])
        changed=DataReader(f.memory(),f.module,dictionary_hashes=hints)
        self.assertEqual(changed.dictionary(dictionary,wanted={'model'})['model'],f.a['host'])
        f.set(keys+35,'<b',7)
        with self.assertRaisesRegex(PythonLayoutError,'index is outside'):
            DataReader(f.memory(),f.module,dictionary_hashes=hints).dictionary(dictionary,wanted={'model'})

    def test_indices_backlinks_bounds_tags_and_membership_fail_without_defaults(self):
        for fault in ['index','backlink','length','tag','membership','cycle','mask']:
            f=StateFixture().properties()
            if fault=='index':f.set(f.descriptors['server_hp'],'<i',-1)
            elif fault=='backlink':f.set(f.a['storage']+8,'<Q',f.a['schema'])
            elif fault=='length':f.set(f.a['storage']+0x20,'<Q',f.a['values']+8)
            elif fault=='tag':f.set(f.a['values']+8,'<B',2)
            elif fault=='membership':
                begin=int.from_bytes(f.memory().read(f.a['schema']+0x40,8),'little')
                f.set(f.a['schema']+0x48,'<Q',begin)
            elif fault=='cycle':f.set(f.a['property_node']+8,'<Q',f.a['property_node'])
            else:f.set(f.a['name_index']+0x40,'<Q',2)
            with self.subTest(fault=fault),self.assertRaises((PythonLayoutError,ValueError)):
                NumericMap(DataReader(f.memory(),f.module),f.a['owner']).read({'server_hp'})

    def test_direct_python_host_rejects_missing_reverse_primary_link(self):
        f=StateFixture()
        f.set(f.a['wrapper_keys']+48,'<Q',f.a['host'])
        frame=process_frame(f.memory(),f.module)
        self.assertEqual(frame.scene.actors[0].classification.category,Category.UNKNOWN)
        self.assertIn('primary association',frame.scene.actors[0].classification.evidence)

    def test_direct_host_and_distinct_area_owner_association(self):
        f=StateFixture().runtime()
        f.set(f.a['wrapper_keys']+48,'<Q',f.a['host'])
        f.set(f.a['instance']+0x10,'<Q',f.dictionary({'model':f.a['python'],'owner':f.a['host']}))
        association=f.alloc(8,[(0,'<Q',[f.a['host']])])
        f.set(f.a['native_area']+0x38,'<Q',association)
        frame=process_frame(f.memory(),f.module)
        state=frame.scene.actors[0].classification
        self.assertEqual(state.category,Category.PLAYER)
        self.assertIs(state.local,True)

    def test_local_context_from_builtin_client_environment(self):
        f=StateFixture().runtime()
        cls=f.type(0x200900000,'ClientEnv')
        attrs=f.dictionary({'player':f.a['host'],'main_player':f.a['host'],
                            'replay_player':f.module.base+0x7A0A150})
        env=f.alloc(40,[(0,'<QQQ',[1,cls,attrs])])
        globals_dict=f.dictionary({'__name__':f.ascii('builtins'),'genv':env})
        builtins=f.alloc(56,[(0,'<QQQ',[1,f.module.base+0x7A1B1F0,globals_dict])])
        f.set(f.interpreter+0x1DE8,'<Q',f.dictionary({'builtins':builtins}))
        context,host,area=local_player(DataReader(f.memory(),f.module))
        self.assertEqual((context.module,host,area),(env,f.a['host'],f.a['owner']))

    def test_primary_model_crosslinks_reject_old_or_secondary_instances(self):
        for side in ['host','instance']:
            f=StateFixture()
            target=f.a['host'] if side=='host' else f.a['instance']
            dictionary=f.dictionary({'model':f.a['owner']})
            f.set(target+0x10,'<Q',dictionary)
            frame=process_frame(f.memory(),f.module)
            state=frame.scene.actors[0].classification
            with self.subTest(side=side):
                self.assertEqual(state.category,Category.UNKNOWN)
                self.assertIn('primary association',state.evidence)

    def test_primary_avatar_model_uses_managed_storage_through_the_full_pipeline(self):
        f=StateFixture().runtime().properties()
        cls=int.from_bytes(f.memory().read(f.a['instance']+8,8),'little')
        f.set(cls+0xA8,'<I',0x1210)  # Heap managed dict, without inline values.
        model_dict=f.dictionary({'model':f.a['python']})
        prefix=f.alloc(24+48,[(0,'<Q',[model_dict]),(24,'<QQ',[1,cls])])
        instance=prefix+24
        f.set(f.a['wrapper_keys']+64,'<Q',instance)
        f.set(f.a['host']+0x10,'<Q',f.dictionary({'model':instance}))
        frame=process_frame(f.memory(),f.module)
        state=frame.scene.actors[0].classification
        self.assertEqual(state.category,Category.PLAYER)
        self.assertIs(state.local,True)
        self.assertEqual({v.name:v.value for v in state.facts.values}['server_hp'],100.0)

    def test_zero_hp_and_unreadable_properties_do_not_invent_life_state(self):
        for fault in ['zero_hp','unsupported_tag']:
            f=StateFixture().runtime().properties({'server_hp':('float',0.0)})
            if fault=='unsupported_tag':f.set(f.a['values']+8,'<B',2)
            frame=process_frame(f.memory(),f.module)
            state=frame.scene.actors[0].classification
            with self.subTest(fault=fault):
                self.assertEqual(state.category,Category.PLAYER)
                self.assertIsNone(state.alive)
                self.assertIsNone(state.visible)
                self.assertIsNone(frame.aim.target)
                if fault=='zero_hp':self.assertEqual(state.facts.values[0].value,0.0)
                else:
                    self.assertFalse(state.facts.values)
                    self.assertIn('numeric properties',state.facts.diagnostics[0])


if __name__=='__main__':unittest.main()
