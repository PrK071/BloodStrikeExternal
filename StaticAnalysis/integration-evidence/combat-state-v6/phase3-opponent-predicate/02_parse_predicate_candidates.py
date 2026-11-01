from pathlib import Path
import runpy,json,hashlib
EV=Path('StaticAnalysis/integration-evidence');IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf8'));DEC=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload'];Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader'];hits=json.load(open('StaticAnalysis/integration-evidence/combat-state-v6/phase3-opponent-predicate/01-literal-scan.json',encoding='utf8'))['hits'];INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
terms={'IsEnemy','CanDamage','IsTeammate','IsFriend','IGameLogicBase','CGameLogicBase'}
out=[]
for hit in hits:
 row=next(x for x in IDX['results'] if x['index']==hit['index']);p=INSTALL/('Resources'+('' if row['package']==0 else str(row['package']))+'.mpk')
 with p.open('rb') as f:f.seek(row['offset']);raw=f.read(row['size'])
 assert hashlib.sha256(raw).hexdigest()==row['compressed_sha256'];data=DEC(raw,8388608);assert hashlib.sha256(data).hexdigest()==row['decoded_sha256'];rd=Reader(data);rd.obj();assert rd.p==len(data)
 selected=[]
 for c in rd.codes:
  strings=[x for x in c.get('consts',[]) if isinstance(x,str)]
  if any(t in c['qualname'] for t in terms) or any(t in c.get('names',[]) for t in terms) or any(t in strings for t in terms):
   selected.append({'qualname':c['qualname'],'filename':c.get('filename'),'line':c.get('firstlineno'),'names':c.get('names',[]),'localsplusnames':c.get('localsplusnames',[]),'strings':strings,'code_sha256':hashlib.sha256(c['code']).hexdigest(),'marshal_offset':c.get('marshal_offset')})
 if selected:out.append({'index':row['index'],'path':row['filename_candidates'],'decoded_sha256':row['decoded_sha256'],'selected':selected})
Path(__file__).with_name('02-predicate-code-candidates.json').write_text(json.dumps({'parsed_candidates':len(hits),'positive_code_modules':len(out),'modules':out},indent=2)+'\n',encoding='utf8')
for m in out:
 for c in m['selected']:
  if any(x in c['qualname'] for x in ['IsEnemy','CanDamage','IsFriend','IsTeammate','IGameLogicBase','CGameLogicBase']): print(m['index'],m['path'],c['qualname'],c['line'],c['names'])
