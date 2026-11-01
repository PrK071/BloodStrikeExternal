import hashlib,json,runpy
from pathlib import Path
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal'); EV=ROOT/'StaticAnalysis'/'integration-evidence'; IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf-8'))
scan=json.loads((Path(__file__).with_name('02-scan-enum-factory.json')).read_text(encoding='utf-8')); row=next(x for x in scan['matches'] if x['index']==66389);r=next(x for x in IDX['results'] if x['index']==66389);assert (row['compressed_sha256'],row['decoded_sha256'])==(r['compressed_sha256'],r['decoded_sha256'])
DEC=runpy.run_path(str(EV/'assets'/'index_script_candidates.py'))['decode_payload'];Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader'];OP=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions'];INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE'); f=INSTALL/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
with f.open('rb') as h:h.seek(r['offset']);raw=h.read(r['size'])
assert hashlib.sha256(raw).hexdigest()==row['compressed_sha256'];data=DEC(raw,8*1024*1024);assert hashlib.sha256(data).hexdigest()==row['decoded_sha256'];rd=Reader(data);rd.obj();assert rd.p==len(data)
def safe(v):
 if isinstance(v,(str,int,bool,type(None),float)):return v
 if isinstance(v,bytes):return {'bytes_hex':v.hex()}
 if isinstance(v,(list,tuple)):return [safe(x) for x in v]
 if isinstance(v,dict):return {str(k):safe(x) for k,x in v.items()}
 return {'type':type(v).__name__,'repr':repr(v)}
def instructions(c):
 b=c['code']; ops=OP([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)]);out=[]
 for x in ops:
  a=x['arg'];v=None
  if x['opname'] in ('LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL') and (a>>1)<len(c.get('names',[])):v=c['names'][a>>1]
  elif x['opname'] in ('STORE_GLOBAL','LOAD_NAME','STORE_NAME','IMPORT_NAME','IMPORT_FROM','STORE_ATTR') and a<len(c.get('names',[])):v=c['names'][a]
  elif 'FAST' in x['opname'] and a<len(c.get('localsplusnames',[])):v=c['localsplusnames'][a]
  elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
   z=c['consts'][a];v=z if isinstance(z,(str,int,bool,type(None),float)) else z.get('qualname',z.get('name')) if isinstance(z,dict) else type(z).__name__
  out.append({'offset':x['offset'],'op':x['opname'],'arg':a,**({'value':v} if v is not None else {})})
 return out
selected=[]
for c in rd.codes:
 if c['qualname']=='<module>' or 'enum' in c['qualname'].lower() or any(isinstance(z,str) and ('enum' in z.lower() or 'IntEnum' in z) for z in c.get('consts',[])):
  selected.append({'qualname':c['qualname'],'filename':c.get('filename'),'line':c.get('firstlineno'),'argcount':c.get('argcount'),'localsplusnames':c.get('localsplusnames',[]),'names':c.get('names',[]),'constants':safe(c.get('consts',[])),'code_sha256':hashlib.sha256(c['code']).hexdigest(),'instructions':instructions(c)})
out={'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','index_sha256':IDX['index_sha256'],'index':66389,'package':r['package'],'opaque_id':r['opaque_id'],'compressed_sha256':row['compressed_sha256'],'decoded_sha256':row['decoded_sha256'],'decoded_size':len(data),'parsed_to_eof':rd.p,'code_objects':len(rd.codes),'selected':selected,'scope':'one literal-path-positive stream; static parse only'}
Path(__file__).with_name('03-enum-factory-definition.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print([(c['qualname'],c['line'],c['code_sha256']) for c in selected])


