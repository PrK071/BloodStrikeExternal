from pathlib import Path
import runpy,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
EV=ROOT/'StaticAnalysis'/'integration-evidence'
IDX=json.loads((EV/'assets'/'script-candidate-index.json').read_text(encoding='utf8'))
DECODE=runpy.run_path(str(EV/'assets'/'index_script_candidates.py'))['decode_payload']
Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader']
OPS=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions']
INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
MODULES={
 107853:['<module>','CombatAvatar','PlayerCombatAvatar'],
 36458:['<module>','with_tag','with_tag.<locals>.warpper'],
 32464:['Components','Components.<locals>._Components','_addComponent','ComponentHost'],
 91687:['<module>','importall','importNormal'],
 61925:['<module>','CombatAvatarMember','CombatAvatarMember.InitAvatarModel'],
 143510:['AvatarModel.__init__','AvatarModel.Load'],
 68957:['SimpleModel.__init__'],
 122267:['BaseModel.__init__'],
 66925:['<module>','ClientEntity.__getattr__','ClientEntity.__setattr__','ClientEntity.onEntityClassRegistered','ClientAreaEntity'],
 119023:['Entity.init_from_dict']
 ,141076:['<module>']
}

def modrow(n): return next(r for r in IDX['results'] if r['index']==n)
def ins_rows(c, lo=None, hi=None):
 b=c['code']; ins=OPS([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)])
 rows=[]
 for x in ins:
  if lo is not None and x['offset']<lo: continue
  if hi is not None and x['offset']>hi: continue
  a=x['arg']; val=None
  if x['opname'] in {'LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL'}:
   j=a>>1
   if j<len(c['names']):val=c['names'][j]
  elif x['opname']=='STORE_ATTR':
   if a<len(c['names']):val=c['names'][a]
  elif x['opname'] in {'LOAD_NAME','STORE_NAME','LOAD_FAST','LOAD_FAST_BORROW','STORE_FAST'}:
   j=a
   pool=c.get('names',[]) if 'NAME' in x['opname'] else c.get('localsplusnames',[])
   if j<len(pool):val=pool[j]
  elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
   v=c['consts'][a]
   val=v if isinstance(v,(str,int,bool,type(None))) else (v.get('qualname',v.get('name')) if isinstance(v,dict) else type(v).__name__)
  rows.append({'offset':x['offset'],'op':x['opname'],'arg':a,**({'resolved':val} if val is not None else {})})
 return rows

def parse(n):
 r=modrow(n);p=INSTALL/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
 data=DECODE(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
 rd=Reader(data);rd.obj();assert rd.p==len(data)
 chosen=[]
 for c in rd.codes:
  if c['qualname'] in MODULES[n]:
   selected_ranges={
    (107853,'<module>'):(480,765),(107853,'CombatAvatar'):(None,None),(107853,'PlayerCombatAvatar'):(None,None),
    (36458,'<module>'):(None,None),(36458,'with_tag'):(None,None),(36458,'with_tag.<locals>.warpper'):(0,260),
    (32464,'Components'):(None,None),(32464,'Components.<locals>._Components'):(72,250),(32464,'_addComponent'):(140,205),(32464,'ComponentHost'):(None,None),
    (91687,'<module>'):(None,None),(91687,'importall'):(None,None),(91687,'importNormal'):(None,None),
    (61925,'<module>'):(330,410),(61925,'CombatAvatarMember'):(None,None),(61925,'CombatAvatarMember.InitAvatarModel'):(30,150),
    (143510,'AvatarModel.__init__'):(0,50),(143510,'AvatarModel.Load'):(800,1175),
    (68957,'SimpleModel.__init__'):(0,50),(122267,'BaseModel.__init__'):(0,40),
    (66925,'<module>'):(None,None),(66925,'ClientEntity.__getattr__'):(0,75),(66925,'ClientEntity.__setattr__'):(0,165),(66925,'ClientEntity.onEntityClassRegistered'):(0,500),(66925,'ClientAreaEntity'):(None,None),
    (119023,'Entity.init_from_dict'):(0,165),
    (141076,'<module>'):(172,198)
   }[(n,c['qualname'])]
   const_idxs={141076:{'<module>':[799]}}.get(n,{}).get(c['qualname'],[])
   chosen.append({'qualname':c['qualname'],'source_filename':c.get('filename'),'name':c['name'],'line':c['firstlineno'],'argcount':c['argcount'],'localsplusnames':c.get('localsplusnames',[]),'names':c.get('names',[]),'string_consts':[v for v in c.get('consts',[]) if isinstance(v,str)],'selected_constants':{str(i):c['consts'][i] for i in const_idxs},'code_sha256':hashlib.sha256(c['code']).hexdigest(),'instructions':ins_rows(c,*selected_ranges)})
 return {'index':n,'filename_candidates':r['filename_candidates'],'source_filenames':sorted({c.get('filename') for c in rd.codes if c.get('filename')}),'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256'],'parsed_to_eof_bytes':rd.p,'code_objects':len(rd.codes),'selected_code':chosen}

result={'index_sha256':IDX['index_sha256'],'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','modules':[parse(n) for n in MODULES],'scope':'static disk decode and marshal parse only; no Python payload imports/eval/execution, game execution, or process access'}
out=Path(__file__).with_name('07-owner-tag-chain-static.json');out.write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps({'modules':[{'index':m['index'],'path':m['filename_candidates'],'sha':m['decoded_sha256'],'code_objects':m['code_objects'],'selected':[c['qualname'] for c in m['selected_code']]} for m in result['modules']]},indent=2,ensure_ascii=True))
