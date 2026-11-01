import sys,struct,hashlib,json,runpy,zlib
from pathlib import Path
HERE=Path(__file__).parent
BASE=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence')
INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
lib=runpy.run_path(str(BASE/'python-format'/'03-static-marshal.py'))
Reader=lib['Reader']
opslib=runpy.run_path(str(BASE/'python-format'/'05-opcodes-selected.py'))
instructions=opslib['instructions']
ids=[37243,94890,122267]
idxbytes=(INSTALL/'Resources.mpkinfo').read_bytes()
assert hashlib.sha256(idxbytes).hexdigest()=='bb3782da03b95d66451a598add8fe0923405be0dde53a8844b2f8bc107a6ced3'
mods=[]
for index in ids:
 ident,off,size,flags=struct.unpack_from('<QQII',idxbytes,8+index*24); pkg=flags>>1
 fpath=INSTALL/('Resources'+('' if pkg==0 else str(pkg))+'.mpk')
 with fpath.open('rb') as f:f.seek(off); raw=f.read(size)
 assert len(raw)==size and raw[:2]==b'\xe2\x06'
 b=bytearray(raw);prefix=min(128-((len(raw)-8)%37),len(raw))
 for j in range(prefix):b[j]^=0x9a
 dec=zlib.decompressobj();data=dec.decompress(bytes(b if prefix==len(raw) else b[:-8]),4*1024*1024+1)
 assert dec.eof and not dec.unused_data and len(data)<=4*1024*1024
 r=Reader(data);root=r.obj();assert r.p==len(data)
 codes=[]
 for c in r.codes:
  ins=instructions([{'opcode':c['code'][i],'arg_byte':c['code'][i+1]} for i in range(0,len(c['code']),2)])
  names=c['names']; consts=c['consts']
  for x in ins:
   x['resolved_name']=names[x['arg']>>1] if x['opname'] in ['LOAD_GLOBAL','LOAD_ATTR','LOAD_METHOD','STORE_ATTR','STORE_GLOBAL'] and (x['arg']>>1)<len(names) else None
   if x['opname']=='LOAD_CONST':
    v=consts[x['arg']];x['const']=({'code':v.get('name'),'qualname':v.get('qualname')} if isinstance(v,dict) and v.get('kind')=='code' else v if isinstance(v,(str,int,float,bool,type(None))) else str(type(v).__name__))
  codes.append({'name':c['name'],'qualname':c['qualname'],'filename':c['filename'],'firstlineno':c['firstlineno'],'marshal_offset':c['marshal_offset'],'names':names,'consts':[v if isinstance(v,(str,int,float,bool,type(None))) else {'code':v.get('qualname')} if isinstance(v,dict) and v.get('kind')=='code' else type(v).__name__ for v in consts],'instructions':ins})
 mods.append({'index':index,'opaque_id':hex(ident),'package':pkg,'offset':off,'compressed_size':size,'compressed_sha256':hashlib.sha256(raw).hexdigest(),'decoded_sha256':hashlib.sha256(data).hexdigest(),'decoded_size':len(data),'marshal_consumed':r.p,'code_count':len(codes),'codes':codes})
(HERE/'resource-code-static.json').write_text(json.dumps({'index_sha256':hashlib.sha256(idxbytes).hexdigest(),'modules':mods},indent=2,ensure_ascii=True))
print(json.dumps([{'index':m['index'],'hash':m['decoded_sha256'],'codes':m['code_count'],'file':m['codes'][0]['filename']} for m in mods]))
