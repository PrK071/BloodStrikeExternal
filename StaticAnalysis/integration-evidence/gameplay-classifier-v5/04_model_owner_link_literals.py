from pathlib import Path
import runpy,json,hashlib,contextlib
O=Path(__file__).resolve().parent;R=O.parent;idx=json.load(open(R/'assets/script-candidate-index.json',encoding='utf8'))
dec=runpy.run_path(str(R/'assets/index_script_candidates.py'))['decode_payload'];terms=[b'AvatarModel',b'PlayerAvatarModel',b'NativeEntity',b'UserData',b'owner']
install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE');out=[]
with contextlib.ExitStack() as st:
 fs={n:st.enter_context((install/('Resources'+('' if n==0 else str(n))+'.mpk')).open('rb')) for n in {r['package'] for r in idx['results']}}
 for r in idx['results']:
  f=fs[r['package']];f.seek(r['offset']);raw=f.read(r['size'])
  assert hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
  data=dec(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
  hits={t.decode():data.count(t) for t in terms if t in data}
  if any(k in hits for k in ('AvatarModel','PlayerAvatarModel','NativeEntity','UserData')):
   out.append({'index':r['index'],'filename_candidates':r['filename_candidates'],'decoded_sha256':r['decoded_sha256'],'hits':hits,'bytes':len(data)})
(O/'04_model-owner-link-literals.json').write_text(json.dumps({'entries_scanned':len(idx['results']),'source_index_sha256':idx['index_sha256'],'terms':[x.decode() for x in terms],'positive_streams':out,'bytecode_executed':False},indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps(out,indent=2,ensure_ascii=True))
