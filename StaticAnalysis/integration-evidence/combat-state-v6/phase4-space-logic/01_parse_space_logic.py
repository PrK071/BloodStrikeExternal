from pathlib import Path
import runpy,json,hashlib
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal'); EV=ROOT/'StaticAnalysis'/'integration-evidence'; IDX=json.loads((EV/'assets/script-candidate-index.json').read_text()); DEC=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload']; Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader']; OPS=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions']; INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
IDS=[118280,29779,38405,94048]
def row(n):return next(x for x in IDX['results'] if x['index']==n)
def decinstr(c):
 b=c['code']; ins=OPS([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)]); out=[]
 for x in ins:
  a=x['arg']; v=None
  if x['opname'] in {'LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL'} and a>>1<len(c.get('names',[])):v=c['names'][a>>1]
  elif x['opname']=='STORE_ATTR' and a<len(c.get('names',[])):v=c['names'][a]
  elif 'FAST' in x['opname'] and a<len(c.get('localsplusnames',[])):v=c['localsplusnames'][a]
  elif 'NAME' in x['opname'] and a<len(c.get('names',[])):v=c['names'][a]
  elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
   z=c['consts'][a];v=z if isinstance(z,(str,int,bool,type(None))) else z.get('qualname',z.get('name')) if isinstance(z,dict) else type(z).__name__
  if x['opname']=='COMPARE_OP': v={'arg':a,'operator':['<','<=','==','!=','>','>='][a>>5],'bool_result':bool(a&16)}
  out.append({'offset':x['offset'],'op':x['opname'],'arg':a,**({'value':v} if v is not None else {})})
 return out
mods=[]
for n in IDS:
 r=row(n); f=INSTALL/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with f.open('rb') as h:h.seek(r['offset']);raw=h.read(r['size'])
 assert len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['compressed_sha256']; data=DEC(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256'];rd=Reader(data);rd.obj();assert rd.p==len(data)
 chosen=[]
 for c in rd.codes:
  names=c.get('names',[]);lc=c.get('localsplusnames',[]);q=c['qualname']
  if not (q=='<module>' or any(s in names for s in ('game_logic','space','genv')) or any(s in q.lower() for s in ('space','gameplay','genv'))):continue
  chosen.append({'qualname':q,'filename':c.get('filename'),'line':c.get('firstlineno'),'localsplusnames':lc,'names':names,'string_consts':[x for x in c.get('consts',[]) if isinstance(x,str)],'code_sha256':hashlib.sha256(c['code']).hexdigest(),'instructions':decinstr(c)})
 mods.append({'index':n,'paths':r['filename_candidates'],'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256'],'parsed_to_eof':rd.p,'code_objects':len(rd.codes),'selected':chosen})
out={'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','index_sha256':IDX['index_sha256'],'scope':'disk-only static MPK decompression and marshal/opcode parse; no import/eval, target execution, or process access','modules':mods}
Path(__file__).with_name('01-space-logic-candidates.json').write_text(json.dumps(out,indent=2)+'\n')
for m in mods:print(m['index'],m['paths'],'codes',m['code_objects'],'selected',len(m['selected']))

