import hashlib,json,runpy,struct
from pathlib import Path
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal'); EV=ROOT/'StaticAnalysis'/'integration-evidence'
IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf-8'))
SCAN=json.loads((Path(__file__).with_name('00-combatstate-literal-scan.json')).read_text(encoding='utf-8'))
row=next(x for x in SCAN['literal_hits'] if x['index']==141076)
assert row['filename_candidates_expanded']==['gshare/consts.py']
r=next(x for x in IDX['results'] if x['index']==141076)
assert row['compressed_sha256']==r['compressed_sha256'] and row['decoded_sha256']==r['decoded_sha256']
DEC=runpy.run_path(str(EV/'assets'/'index_script_candidates.py'))['decode_payload']
Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader']
OP=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions']
INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE');f=INSTALL/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
with f.open('rb') as h:h.seek(r['offset']);raw=h.read(r['size'])
assert hashlib.sha256(raw).hexdigest()==row['compressed_sha256']
data=DEC(raw,8*1024*1024);assert hashlib.sha256(data).hexdigest()==row['decoded_sha256']
rd=Reader(data);rd.obj();assert rd.p==len(data)
def ins(c):
 b=c['code'];ops=OP([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)]);out=[]
 for x in ops:
  a=x['arg'];v=None
  if x['opname'] in ('LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL') and (a>>1)<len(c.get('names',[])):v=c['names'][a>>1]
  elif x['opname'] in ('STORE_GLOBAL','LOAD_NAME','STORE_NAME','IMPORT_NAME','IMPORT_FROM','STORE_ATTR') and a < len(c.get('names',[])):v=c['names'][a]
  elif 'FAST' in x['opname'] and a < len(c.get('localsplusnames',[])):v=c['localsplusnames'][a]
  elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
   z=c['consts'][a];v=z if isinstance(z,(str,int,bool,type(None),float)) else z.get('qualname',z.get('name')) if isinstance(z,dict) else type(z).__name__
  out.append({'offset':x['offset'],'op':x['opname'],'arg':a,**({'value':v} if v is not None else {})})
 return out
def safe(v):
 if isinstance(v,(str,int,bool,type(None),float)): return v
 if isinstance(v,bytes): return {'bytes_hex':v.hex()}
 if isinstance(v,(list,tuple)): return [safe(x) for x in v]
 if isinstance(v,dict): return {str(k):safe(x) for k,x in v.items()}
 return {'type':type(v).__name__,'repr':repr(v)}
codes=[]
for c in rd.codes:
 if c['qualname']=='<module>' or c['qualname'].split('.')[-1] in ('CombatState','__new__','__init__','__getattr__','__int__','__index__') or any(isinstance(z,str) and z in ('CombatState','ALIVE','DYING') for z in c.get('consts',[])):
  codes.append({'qualname':c['qualname'],'filename':c.get('filename'),'line':c.get('firstlineno'),'argcount':c.get('argcount'),'localsplusnames':c.get('localsplusnames',[]),'names':c.get('names',[]),'constants':safe(c.get('consts',[])),'code_sha256':hashlib.sha256(c['code']).hexdigest(),'instructions':ins(c)})
out={'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','index_sha256':IDX['index_sha256'],'index':141076,'package':r['package'],'opaque_id':r['opaque_id'],'compressed_sha256':row['compressed_sha256'],'decoded_sha256':row['decoded_sha256'],'decoded_size':len(data),'parsed_to_eof':rd.p,'code_objects':len(rd.codes),'selected':codes,'scope':'one literal-positive MPK stream; static marshal/opcode parse; no execution/import/process access'}
Path(__file__).with_name('01-combatstate-definition.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('selected',[(c['qualname'],c['line'],c['code_sha256']) for c in codes])




