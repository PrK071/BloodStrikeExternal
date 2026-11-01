from pathlib import Path
import runpy,json,hashlib,contextlib
O=Path(__file__).resolve().parent; R=O.parent
index=json.loads((R/'assets/script-candidate-index.json').read_text(encoding='utf8'))
decode=runpy.run_path(str(R/'assets/index_script_candidates.py'))['decode_payload']
terms=[b'IsPlayerCombatAvatar',b'IsCombatAvatar',b'IsATMGuardAI',b'owner',b'PlayerCombatAvatar']
install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
found=[];total=0;bytes_scanned=0
with contextlib.ExitStack() as stack:
 fs={n:stack.enter_context((install/('Resources'+('' if n==0 else str(n))+'.mpk')).open('rb')) for n in {x['package'] for x in index['results']}}
 for row in index['results']:
  f=fs[row['package']];f.seek(row['offset']);raw=f.read(row['size'])
  if hashlib.sha256(raw).hexdigest()!=row['compressed_sha256']:raise ValueError(f"compressed hash mismatch {row['index']}")
  payload=decode(raw,8388608)
  if hashlib.sha256(payload).hexdigest()!=row['decoded_sha256']:raise ValueError(f"decoded hash mismatch {row['index']}")
  bytes_scanned+=len(payload);hits={t.decode():payload.count(t) for t in terms if t in payload}
  if hits:
   found.append({k:row[k] for k in ['index','package','offset','size','compressed_sha256','decoded_sha256','filename_candidates'] }|{'hits':hits,'payload_bytes':len(payload)})
  total+=1
out={'source_index_sha256':index['index_sha256'],'entries_scanned':total,'decoded_bytes_scanned':bytes_scanned,'terms':[x.decode() for x in terms],'positive_streams':found,'execution':'no bytecode executed'}
(O/'01-literal-owner-search.json').write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps({'entries':total,'bytes':bytes_scanned,'positive_count':len(found),'matches':[{k:r[k] for k in ['index','filename_candidates','hits']} for r in found]},indent=2))
