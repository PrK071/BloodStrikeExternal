import json,runpy,hashlib,contextlib
from pathlib import Path
R=Path('StaticAnalysis/integration-evidence');idx=json.load(open(R/'assets/script-candidate-index.json',encoding='utf8'));dec=runpy.run_path(str(R/'assets/index_script_candidates.py'))['decode_payload'];terms=[b'CombatAvatarMember',b'PlayerCombatAvatarMember',b'avatar_model']
ins=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE');out=[]
with contextlib.ExitStack() as s:
 fs={n:s.enter_context((ins/('Resources'+('' if n==0 else str(n))+'.mpk')).open('rb')) for n in {r['package'] for r in idx['results']}}
 for r in idx['results']:
  f=fs[r['package']];f.seek(r['offset']);raw=f.read(r['size']);assert hashlib.sha256(raw).hexdigest()==r['compressed_sha256'];data=dec(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
  h={t.decode():data.count(t) for t in terms if t in data}
  if h:out.append({'index':r['index'],'path':r['filename_candidates'],'hash':r['decoded_sha256'],'hits':h})
(R/'gameplay-classifier-v5'/'05_component-owner-literals.json').write_text(json.dumps({'source_index_sha256':idx['index_sha256'],'entries_scanned':len(idx['results']),'terms':[t.decode() for t in terms],'matches':out,'bytecode_executed':False},indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps(out,indent=2,ensure_ascii=True))
