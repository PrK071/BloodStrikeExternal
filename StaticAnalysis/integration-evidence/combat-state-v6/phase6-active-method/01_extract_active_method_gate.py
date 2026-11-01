import json
from pathlib import Path
root=Path(__file__).parents[1]
# phase 6 lives under integration-evidence/combat-state-v6/phase6-active-method
root=Path(__file__).parents[1]
base=root
p3=base/'phase3-opponent-predicate/03-general-and-mode-predicates.json'
p4=base/'phase4-space-logic/01-space-logic-candidates.json'
p5=base/'phase5-aim-eligibility/01-aim-state-candidates.json'
for p in (p3,p4,p5):
    assert p.exists(),p
D3=json.loads(p3.read_text(encoding='utf-8')); D4=json.loads(p4.read_text(encoding='utf-8')); D5=json.loads(p5.read_text(encoding='utf-8'))
TARGET='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
for d in (D3,D4,D5): assert d['target_sha256']==TARGET

def mod(d,idx): return next(x for x in d['modules'] if x['index']==idx)
def code(d,idx,q): return next(x for x in mod(d,idx)['selected'] if x['qualname']==q)
def inst(c,lo,hi): return [x for x in c['instructions'] if lo<=x['offset']<=hi]
# CGameLogicBase explicitly subclasses IGameLogicBase; Games are decorated/assembled with Components.
cbase=code(D3,145546,'CGameLogicBase')
module=code(D3,145546,'<module>')
ig=code(D3,108818,'IGameLogicBase')
base_enemy=code(D3,108818,'IGameLogicBase.IsEnemy')
# Active method candidates already parsed in bounded phase3.
overrides=[]
for idx,q in [(92227,'MobaFactionMapInfoMixin.IsEnemy'),(132180,'CGameLogicPeekaboo.IsEnemy'),(80751,'GameLogicZombieComp.IsEnemy')]:
 c=code(D3,idx,q); m=mod(D3,idx)
 overrides.append({'index':idx,'path':m['paths'],'decoded_sha256':m['decoded_sha256'],'qualname':q,'code_sha256':c['code_sha256'],'argcount':c.get('argcount'),'names':c.get('names',[])})
# Resolvers/hooks present in bounded classes.
hooks={}
for d,idx,qs in [(D3,108818,['IGameLogicBase']), (D3,145546,['CGameLogicBase']), (D4,118280,['ClientSpace']), (D4,29779,['Space'])]:
 m=mod(d,idx)
 hooks[str(idx)]={'path':m['paths'],'decoded_sha256':m['decoded_sha256'],'selected_hooks':[c['qualname'] for c in m['selected'] if c['qualname'].endswith('.__getattr__') or c['qualname'].endswith('.__getattribute__')], 'class':{q:{'code_sha256':code(d,idx,q)['code_sha256'],'has_IsEnemy_name':'IsEnemy' in code(d,idx,q).get('names',[])} for q in qs}}
select=code(D5,68262,'AssistAim.SelectTarget'); aim_mod=mod(D5,68262)
space=code(D4,29779,'Space'); space_init=code(D4,29779,'Space.init'); space_enter=code(D4,29779,'Space.enter')
result={
 'target_sha256':TARGET,'index_sha256':D3['index_sha256'],'scope':'static MPK reports only; no bytecode execution, process inspection, or game launch',
 'active_reference':{'producer_index':29779,'path':mod(D4,29779)['paths'],'decoded_sha256':mod(D4,29779)['decoded_sha256'],'Space_init_code_sha256':space_init['code_sha256'],'Space_enter_code_sha256':space_enter['code_sha256'],'producer_observation':'Space.init assigns self.game_logic=None and publishes genv.space=self; Space.enter assigns self.game_logic=entity only when entity.IsGameLogic is truthy. Player ADS code in index 107853 reads genv.space.game_logic and invokes .IsEnemy; AssistAim code uses owner.game_logic.CanDamage.'},
 'general_implementation':{'index':108818,'path':'gshare/game_logic/igame_logic_base.py','decoded_sha256':mod(D3,108818)['decoded_sha256'],'qualname':'IGameLogicBase.IsEnemy','code_sha256':base_enemy['code_sha256'],'argcount':base_enemy['argcount'],'localsplusnames':base_enemy['localsplusnames'],'base_class_body_sha256':ig['code_sha256'],'finding':'canonical general body is defined in IGameLogicBase; CGameLogicBase class body has no IsEnemy method and is built as a subclass of IGameLogicBase at module offsets 616-636.'},
 'component_composition':{'module_index':145546,'module_sha256':module['code_sha256'],'CGameLogicBase_class_sha256':cbase['code_sha256'],'class_build_instructions':inst(module,616,710),'note':'The module applies Components(...) around the general CGameLogicBase entity. Components-based class composition and mode-specific components mean a class name or IsGameLogic marker alone does not identify the resolved IsEnemy function.'},
 'known_overrides':overrides,
 'attribute_resolution_audit':{'selected_python_hooks':hooks,'limitations':['No selected Python __getattr__ or __getattribute__ body was found in the bounded IGameLogicBase, CGameLogicBase, ClientSpace, or Space reports. This does not rule out hooks on native bases/decorators or outside the selected module scope.','Space inherits a native-facing ClientSpace/Entity/SpaceClass path; no proof here excludes native descriptors or proves the external storage slot for Space.game_logic.','Components and mixins alter class dictionaries; an active runtime type/MRO must be inspected. An instance attribute could also shadow a non-data Python function descriptor. No selected artifacts establish absence of an instance-level IsEnemy override.']},
 'conservative_gate':{'needed_runtime_evidence':['Read the actual active object reached through genv.space.game_logic (or the same object used by the consumer).','Resolve the actual IsEnemy attribute following instance and type/MRO lookup, including component-injected class dictionary entries.','Accept only if the resolved function/code object matches a mode-approved code fingerprint; for base general behavior, IsEnemy code_sha256 must equal the IGameLogicBase.IsEnemy fingerprint above.','Reject unknown wrappers, instance overrides, unresolved/native descriptors, and any other fingerprint.'],'static_only_conclusion':'The original code defines a concrete fingerprintable base function and known mode overrides, but static producers do not identify which function wins for the live active instance. A conservative static-only reader cannot assign the base predicate from the IsGameLogic marker or class-name resemblance.'},
 'assist_aim_state_anchor':{'module_key':'gclient.framework.util.assist_aim_util','path':aim_mod['paths'],'decoded_sha256':aim_mod['decoded_sha256'],'SelectTarget_code_sha256':select['code_sha256'],'argcount':select['argcount'],'localsplusnames':select['localsplusnames'],'class_defaults_bytecode_offsets':[130,132,152,154,160,162],'default_shape':'the method positional defaults contain a single default object: a one-element tuple built as (CombatState.ALIVE,). Runtime anchor: AssistAim.__dict__["SelectTarget"].__defaults__[-1][0]. This retrieves the enum object, not an assumed integer. The source imports CombatState from gshare.consts; underlying numeric encoding and runtime type are not proven.'}
}
out=Path(__file__).with_name('01-active-method-gate.json')
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(out)

