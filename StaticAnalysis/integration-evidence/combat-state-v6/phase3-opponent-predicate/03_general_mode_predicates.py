from pathlib import Path
import runpy,json,hashlib
EV=Path('StaticAnalysis/integration-evidence');IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf8'));DEC=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload'];Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader'];OPS=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions'];INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
MODS={85021:{'GameLogicMoba','<module>'},108818:{'IGameLogicBase.CanDamage','IGameLogicBase.IsEnemy','IGameLogicBase.IsFriend','IGameLogicBase.GetOption','IGameLogicBase','<module>'},145546:{'CGameLogicBase','GameLogicBase','ReplayGameLogicBase','<module>','CGameLogicBase.IsTeammate','GameLogicBase.player'},92227:{'MobaFactionMapInfoMixin','<module>','MobaFactionMapInfoMixin.IsEnemy','MobaFactionMapInfoMixin.IsFriend','MobaFactionMapInfoMixin.IsTeammate'},132180:{'CGameLogicPeekaboo','<module>','CGameLogicPeekaboo.IsEnemy','CGameLogicPeekaboo.IsTeammate','CGameLogicPeekaboo.CanDamage'},80751:{'GameLogicZombieComp','GameLogicZombieComp.CanDamage','GameLogicZombieComp.IsEnemy'}}
cmp=['<','<=','==','!=','>','>=']
def row(n):return next(x for x in IDX['results'] if x['index']==n)
def instr(c):
 b=c['code'];ins=OPS([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)]);out=[]
 jumpops={'JUMP_FORWARD','JUMP_BACKWARD','JUMP_BACKWARD_NO_INTERRUPT','POP_JUMP_IF_FALSE','POP_JUMP_IF_TRUE','POP_JUMP_IF_NONE','POP_JUMP_IF_NOT_NONE','FOR_ITER'}
 for x in ins:
  a=x['arg'];v=None;target=None
  if x['opname'] in {'LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL'} and a>>1<len(c['names']):v=c['names'][a>>1]
  elif x['opname']=='STORE_ATTR' and a<len(c['names']):v=c['names'][a]
  elif x['opname'] in {'LOAD_FAST_LOAD_FAST','LOAD_FAST_BORROW_LOAD_FAST_BORROW','STORE_FAST_LOAD_FAST','STORE_FAST_STORE_FAST'}:
   ids=(a>>4,a&15);v=[c.get('localsplusnames',[])[i] if i<len(c.get('localsplusnames',[])) else None for i in ids]
  elif 'FAST' in x['opname'] and a<len(c.get('localsplusnames',[])):v=c['localsplusnames'][a]
  elif 'NAME' in x['opname'] and a<len(c.get('names',[])):v=c['names'][a]
  elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
   z=c['consts'][a];v=z if isinstance(z,(str,int,bool,type(None))) else z.get('qualname',z.get('name')) if isinstance(z,dict) else type(z).__name__
  if x['opname']=='COMPARE_OP':v={'operator':cmp[a>>5],'bool_result':bool(a&16),'flags':a&15}
  if x['opname'] in jumpops:
   signed=-a if x['opname'] in {'JUMP_BACKWARD','JUMP_BACKWARD_NO_INTERRUPT'} else a
   target=x['offset']+2+signed*2+x['cache_words']*2
  row={'offset':x['offset'],'op':x['opname'],'arg':a,**({'value':v} if v is not None else {}),**({'target':target} if target is not None else {})}
  out.append(row)
 return out
mods=[]
for n,qs in MODS.items():
 r=row(n);p=INSTALL/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['compressed_sha256'];data=DEC(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256'];rd=Reader(data);rd.obj();assert rd.p==len(data)
 chosen=[]
 for c in rd.codes:
  if c['qualname'] not in qs:continue
  chosen.append({'qualname':c['qualname'],'filename':c.get('filename'),'line':c.get('firstlineno'),'argcount':c.get('argcount'),'posonlyargcount':c.get('posonlyargcount'),'kwonlyargcount':c.get('kwonlyargcount'),'flags':c.get('flags'),'localsplusnames':c.get('localsplusnames',[]),'names':c.get('names',[]),'string_consts':[z for z in c.get('consts',[]) if isinstance(z,str)],'code_sha256':hashlib.sha256(c['code']).hexdigest(),'instructions':instr(c)})
 mods.append({'index':n,'paths':r['filename_candidates'],'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256'],'parsed_to_eof':rd.p,'code_objects':len(rd.codes),'selected':chosen})
Path(__file__).with_name('03-general-and-mode-predicates.json').write_text(json.dumps({'index_sha256':IDX['index_sha256'],'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','compare_op_decode':'CPython 3.14.0: operator index = oparg >> 5; bool conversion flag = oparg & 16; source: Lib/dis.py ArgResolver.get_argval_argrepr and Python/bytecodes.c _COMPARE_OP','scope':'disk-only static MPK decode/parse; no Python bytecode or game/process execution','modules':mods},indent=2)+'\n',encoding='utf8')
for m in mods:print(m['index'],m['paths'],[(c['qualname'],c['line'],c['argcount']) for c in m['selected']])
