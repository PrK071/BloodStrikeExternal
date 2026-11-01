from pathlib import Path
import json,hashlib
O=Path(__file__).parent;P=O.parent/'camera-binding'
rows=json.loads((P/'screenpoint-callers-static.json').read_text());out=[]
for r in rows:
 if r['index']!=71683:continue
 for c in r['codes']:
  if c['qualname'] in ['CommonTopLogo.CreateMarkToplogo','CommonTopLogo.UpdateMarkToplogo','CommonTopLogo._UpdateMarkToplogo','CommonTopLogo.GetScreenPointFromWorldPointPython'] or any(x.get('symbol')=='mark_toplogo_pos' and x['opname']=='STORE_ATTR' for x in c['instructions']):
   out.append(dict(index=r['index'],decoded_sha256=r['decoded_sha256'],qualname=c['qualname'],marshal_offset=c['marshal_offset'],instructions=c['instructions']))
(O/'selected-producer-flow.json').write_text(json.dumps(out,indent=2))
print([(x['qualname'],x['marshal_offset']) for x in out])
manifest={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file()}
manifest['upstream-screenpoint-callers-static.json']=hashlib.sha256((P/'screenpoint-callers-static.json').read_bytes()).hexdigest()
(O/'manifest.json').write_text(json.dumps(manifest,indent=2))
