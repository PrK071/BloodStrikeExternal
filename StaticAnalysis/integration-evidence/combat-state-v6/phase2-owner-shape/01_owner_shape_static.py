from pathlib import Path
import runpy,json,hashlib
ROOT=Path(__file__).resolve().parents[4];EV=ROOT/'StaticAnalysis'/'integration-evidence';IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf8'));DEC=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload'];R=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader'];OPS=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions'];INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
MODS={107853:['<module>','PlayerCombatAvatar'],117964:['<module>','ModelComponent','ModelComponent.__init_component__','ModelComponent.__post_component__'],119023:['<module>','Entity','Entity.__init__','Entity.__getattr__'],66925:['<module>','ClientEntity','ClientEntity.__getattr__','ClientEntity.__setattr__','ClientAreaEntity','ClientAreaEntity.__init__'],32464:['<module>','_addComponent','ComponentHost','Components','Components.<locals>._Components'],61925:['<module>','CombatAvatarMember','CombatAvatarMember.InitAvatarModel']}
def getrow(n):return next(x for x in IDX['results'] if x['index']==n)
def resolve(c):
 b=c['code'];ins=OPS([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)]);out=[]
 for x in ins:
  a=x['arg'];v=None
  if x['opname'] in {'LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL'} and a>>1<len(c['names']):v=c['names'][a>>1]
  elif x['opname']=='STORE_ATTR' and a<len(c['names']):v=c['names'][a]
  elif 'FAST' in x['opname'] and a<len(c.get('localsplusnames',[])):v=c['localsplusnames'][a]
  elif 'NAME' in x['opname'] and a<len(c.get('names',[])):v=c['names'][a]
  elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
   q=c['consts'][a];v=q if isinstance(q,(str,int,bool,type(None))) else q.get('qualname',q.get('name')) if isinstance(q,dict) else type(q).__name__
  out.append({'offset':x['offset'],'op':x['opname'],'arg':a,**({'value':v} if v is not None else {})})
 return out
mods=[]
for n,qs in MODS.items():
 row=getrow(n);p=INSTALL/('Resources'+('' if row['package']==0 else str(row['package']))+'.mpk')
 with p.open('rb') as f:f.seek(row['offset']);raw=f.read(row['size'])
 assert hashlib.sha256(raw).hexdigest()==row['compressed_sha256'];data=DEC(raw,8388608);assert hashlib.sha256(data).hexdigest()==row['decoded_sha256'];rd=R(data);rd.obj();assert rd.p==len(data)
 cs=[]
 for c in rd.codes:
  if c['qualname'] in qs:cs.append({'qualname':c['qualname'],'line':c.get('firstlineno'),'filename':c.get('filename'),'localsplusnames':c.get('localsplusnames',[]),'names':c.get('names',[]),'const_names':[v.get('qualname',v.get('name')) if isinstance(v,dict) else v for v in c.get('consts',[]) if isinstance(v,(str,dict))],'code_sha256':hashlib.sha256(c['code']).hexdigest(),'instructions':resolve(c)})
 mods.append({'index':n,'paths':row['filename_candidates'],'decoded_sha256':row['decoded_sha256'],'compressed_sha256':row['compressed_sha256'],'parsed_to_eof':rd.p,'code_objects':len(rd.codes),'selected':cs})
out={'index_sha256':IDX['index_sha256'],'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','scope':'static MPK decode and marshal parse only; no payload execution, game or process access','modules':mods}
Path(__file__).with_name('01-owner-shape-static.json').write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print([(x['index'],x['paths'],[c['qualname'] for c in x['selected']]) for x in mods])
