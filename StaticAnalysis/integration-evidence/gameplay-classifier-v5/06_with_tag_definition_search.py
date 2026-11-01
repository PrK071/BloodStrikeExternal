import runpy,json,hashlib,contextlib
from pathlib import Path
R=Path('StaticAnalysis/integration-evidence');idx=json.load(open(R/'assets/script-candidate-index.json',encoding='utf8'));dec=runpy.run_path(str(R/'assets/index_script_candidates.py'))['decode_payload'];Reader=runpy.run_path(str(R/'python-format/03-static-marshal.py'))['Reader'];ins=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE');out=[];literal_ids=[]
with contextlib.ExitStack() as st:
 fs={n:st.enter_context((ins/('Resources'+('' if n==0 else str(n))+'.mpk')).open('rb')) for n in {r['package'] for r in idx['results']}}
 for r in idx['results']:
  f=fs[r['package']];f.seek(r['offset']);raw=f.read(r['size']);assert hashlib.sha256(raw).hexdigest()==r['compressed_sha256'];data=dec(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
  if b'with_tag' not in data:continue
  literal_ids.append(r['index']);rd=Reader(data);rd.obj();assert rd.p==len(data)
  defs=[{'name':c['name'],'qualname':c['qualname'],'line':c['firstlineno'],'names':c['names'],'string_consts':[x for x in c['consts'] if isinstance(x,str)]} for c in rd.codes if c['name']=='with_tag' or c['qualname'].endswith('.with_tag')]
  if defs:out.append({'index':r['index'],'filename_candidates':r['filename_candidates'],'decoded_sha256':r['decoded_sha256'],'definition_codes':defs})
res={'source_index_sha256':idx['index_sha256'],'literal_with_tag_stream_count':len(literal_ids),'literal_positive_indices':literal_ids,'definition_matches':out,'bytecode_executed':False}
(R/'gameplay-classifier-v5'/'06-with-tag-definition-search.json').write_text(json.dumps(res,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps({'count':len(literal_ids),'definition_matches':out},indent=2,ensure_ascii=True))
