from pathlib import Path
import json
p=Path(__file__).with_name('01-aim-state-candidates.json')
d=json.loads(p.read_text(encoding='utf-8'))
assert d['target_sha256']=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
def module(i): return next(m for m in d['modules'] if m['index']==i)
def code(m,q): return next(c for c in m['selected'] if c['qualname']==q)
def import_rows(i,target):
 c=code(module(i),'<module>'); rows=c['instructions']; out=[]
 for n,x in enumerate(rows):
  if x['op']=='IMPORT_NAME' and x.get('value')==target:
   out.append({'import_name_offset':x['offset'],'next_rows':rows[n:n+8]})
 return out
m682=module(68262); body=code(m682,'AssistAim'); fn=code(m682,'AssistAim.SelectTarget')
m140=module(14066); body140=code(m140,'CombatAvatarMember')
m865=module(86590)
claim={
 'target_sha256':d['target_sha256'],'index_sha256':d['index_sha256'],
 'modules':{str(i):{'paths':module(i)['paths'],'decoded_sha256':module(i)['decoded_sha256'],'gshare_consts_import':import_rows(i,'gshare.consts')} for i in (14066,68262)},
 'AssistAimLocalRootModuleKey':{'candidate_key':'gclient.framework.util.assist_aim_util','path_evidence_index':86590,'path_evidence_module':m865['paths'],'decoded_sha256':m865['decoded_sha256'],'import':import_rows(86590,'gclient.framework.util.assist_aim_util'),'note':'A consumer imports names from this exact path; this identifies the import key for the loaded AssistAim module namespace.'},
 'AssistAim':{'class_body_sha256':body['code_sha256'],'SelectTarget_code_sha256':fn['code_sha256'],'argcount':fn['argcount'],'localsplusnames':fn['localsplusnames'],'default_construction_instructions':[x for x in body['instructions'] if x['offset'] in (130,132,152,154,160,162)],'func_defaults_shape_from_bytecode':'outer one-element defaults tuple whose member is the one-element tuple (CombatState.ALIVE,); argcount=5 and five positional arguments means this is the combat_states default. At runtime the class-dict function __defaults__[-1][0] is the enum member object.'},
 'CombatAvatarMember':{'class_body_sha256':body140['code_sha256'],'combat_state_in_class_co_names':'combat_state' in body140['names'],'combat_state_property_strings':[x for x in body140['string_consts'] if 'combat_state' in x.lower()],'finding':'the selected Python class body has no Property declaration named combat_state or default value for it; native-base descriptor initialization is outside this evidence.'},
 'enum_numeric_encoding':'not present in these MPK code bodies; do not hardcode a numeric value or assume PyLong subclass from this source alone.'}
Path(__file__).with_name('03-combat-state-enum-default-proof.json').write_text(json.dumps(claim,indent=2)+'\n',encoding='utf-8')
