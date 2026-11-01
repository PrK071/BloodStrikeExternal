import json
from pathlib import Path
HERE=Path(__file__).parent
cs=json.loads((HERE/'01-combatstate-definition.json').read_text(encoding='utf-8'))
eu=json.loads((HERE/'03-enum-factory-definition.json').read_text(encoding='utf-8'))
v5=json.loads((Path(__file__).parents[1]/'combat-state-v6'/'phase5-aim-eligibility'/'03-combat-state-enum-default-proof.json').read_text(encoding='utf-8'))
sc=next(c for c in cs['selected'] if c['qualname']=='CombatState')
mod=next(c for c in cs['selected'] if c['qualname']=='<module>')
meta=next(c for c in eu['selected'] if c['qualname']=='EnumMetaclass.__new__')
enum_mod=next(c for c in eu['selected'] if c['qualname']=='<module>')
imp=[]
for i,x in enumerate(mod['instructions']):
 if x['op']=='IMPORT_NAME' and x.get('value')=='gshare.utils': imp=mod['instructions'][i:i+5];break
construction=[]
for i,x in enumerate(mod['instructions']):
 if x['op']=='LOAD_CONST' and x.get('value')=='CombatState':
  if any(y['op']=='LOAD_NAME' and y.get('value')=='enum' for y in mod['instructions'][i:i+8]): construction=mod['instructions'][i-2:i+8];break
assign=[]
for x in sc['instructions']:
 if x['op'] in ('LOAD_SMALL_INT','STORE_NAME') and (x.get('value') in ('ALIVE','DYING','DEAD','GHOST','NONE','SPIRIT') or x['op']=='LOAD_SMALL_INT' and x['arg'] in (0,1,2,3,4,5)):assign.append(x)
relevant_meta=[x for x in meta['instructions'] if x['offset'] in (10,20,42,44,52,54,58,62,64,66,86,88,114,124,126,134,142,152,162,182,184,186,194,202,212,214,216,220,222,224,228,236,238,240,244,246,248,252,262,282,284,286,294)]
# Resolve selected op args against co_names using CPython 3.14 rules.
def resolve(rows,c):
 out=[]
 for x in rows:
  y=dict(x); a=x.get('arg');op=x['op']
  if op in ('LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL') and isinstance(a,int):
   names=c.get('names',[]); y['resolved_name']=names[a>>1] if (a>>1)<len(names) else None
  elif op in ('LOAD_NAME','STORE_NAME','STORE_ATTR','IMPORT_NAME','IMPORT_FROM','STORE_GLOBAL') and isinstance(a,int):
   names=c.get('names',[]); y['resolved_name']=names[a] if a<len(names) else None
  out.append(y)
 return out
result={
 'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','index_sha256':cs['index_sha256'],'scope':'hash-checked MPK stream parse and bytecode analysis only; no module import or code execution',
 'definition':{'mpk_index':cs['index'],'module_path':'gshare/consts.py','module_compressed_sha256':cs['compressed_sha256'],'module_decoded_sha256':cs['decoded_sha256'],'CombatState_line':sc['line'],'CombatState_code_sha256':sc['code_sha256'],'class_body_assignments':assign,'values':{'ALIVE':0,'DYING':1,'DEAD':2,'GHOST':3,'NONE':4,'SPIRIT':5},'module_import_enum':resolve(imp,mod),'class_creation_sequence':resolve(construction,mod),'conclusion':'CombatState class body assigns ALIVE=0, DYING=1. The class is created with enum as its base; enum is imported from gshare.utils.'},
 'enum_factory':{'mpk_index':eu['index'],'module_path':'gshare/utils.py','module_decoded_sha256':eu['decoded_sha256'],'EnumMetaclass_new_line':meta['line'],'EnumMetaclass_new_code_sha256':meta['code_sha256'],'relevant_instructions':resolve(relevant_meta,meta),'analysis':'EnumMetaclass.__new__ iterates the class namespace, excludes dunder/callable/method-descriptor entries from enum-member maps, adds value_to_names and name_to_values mappings, then calls type.__new__(mcs, clsname, bases, bdict) on the original namespace. It does not replace ALIVE or DYING values before type.__new__; their class-dictionary values remain integers 0 and 1. This is a custom enum metaclass, not a stdlib enum.Enum declaration.'},
 'aim_consumer_anchor':{'source_index':68262,'source_path':'gclient/framework/util/assist_aim_util.py','decoded_sha256':v5['AssistAim']['decoded_sha256'] if 'decoded_sha256' in v5.get('AssistAim',{}) else '8163bc535975fd931d2df900fc04bf0d0402e1e5555aa6c2c3d2ffd53168f3de','SelectTarget_code_sha256':v5['AssistAim']['SelectTarget_code_sha256'],'argcount':v5['AssistAim']['argcount'],'localsplusnames':v5['AssistAim']['localsplusnames'],'CombatState_import':resolve(v5['modules']['68262']['gshare_consts_import'][0]['next_rows'][:3],{'names':['gshare.consts','CombatState']}),'default_shape':v5['AssistAim']['func_defaults_shape_from_bytecode'],'runtime_route':'Read the loaded AssistAim.SelectTarget function; verify its code-byte SHA-256, argcount and localsplusnames. Read function.__globals__["CombatState"] (the module import binding), then class dictionary ALIVE and DYING. Cross-check the function default tuple object equals ALIVE. Expected values from pinned source are ALIVE=0 and DYING=1; no generic zero/default inference is involved.'},
 'native_link_boundary':{'pe_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','evidence':'Existing native-properties-v6 evidence establishes numeric property storage and a raw combat_state property path only after dispatch; its bounded standalone PE NUL-string search did not find the combat_state or faction literals. No PE-side symbolic CombatState/ALIVE/DYING binding was found in the reviewed artifacts. The numeric semantic labels here come from the pinned Python MPK schema and the original SelectTarget allow-list, not a guessed native enum.'},
 'opcode_semantics_source':'CPython 3.14 documents LOAD_SMALL_INT as pushing a small integer equal to oparg: https://docs.python.org/3.14/whatsnew/3.14.html#cpython-bytecode-changes'
}
(HERE/'04-combatstate-numeric-contract.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'values':result['definition']['values'],'combatstate_code_sha256':result['definition']['CombatState_code_sha256'],'enum_meta_code_sha256':meta['code_sha256'],'aim_code_sha256':result['aim_consumer_anchor']['SelectTarget_code_sha256'],'import':result['definition']['module_import_enum'],'construction':result['definition']['class_creation_sequence']},indent=2,ensure_ascii=False))
