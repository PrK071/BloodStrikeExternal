from pathlib import Path
import runpy,json,hashlib,contextlib
O=Path(__file__).parent; R=O.parent
lib=runpy.run_path(str(R/'assets/index_script_candidates.py')); dec=lib['decode_payload']
j=json.loads((R/'assets/script-candidate-index.json').read_text()); install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE'); results=[]; total=0
terms=[b'CameraMaster',b'CameraController',b'ControlledCamera',b'AffiliatedCamera']
with contextlib.ExitStack() as s:
 fs={n:s.enter_context((install/('Resources'+('' if n==0 else str(n))+'.mpk')).open('rb')) for n in {x['package'] for x in j['results']}}
 for r in j['results']:
  f=fs[r['package']];f.seek(r['offset']);raw=f.read(r['size']);assert hashlib.sha256(raw).hexdigest()==r['compressed_sha256'];v=dec(raw,8388608);assert hashlib.sha256(v).hexdigest()==r['decoded_sha256'];total+=len(v)
  hits={t.decode():v.count(t) for t in terms if t in v}
  if hits:results.append(dict(index=r['index'],filenames=r['filename_candidates'],hits=hits))
(O/'literal-camera-bindings.json').write_text(json.dumps(dict(entries=len(j['results']),bytes=total,results=results,bytecode_executed=False),indent=2));print(json.dumps(results,indent=2))
