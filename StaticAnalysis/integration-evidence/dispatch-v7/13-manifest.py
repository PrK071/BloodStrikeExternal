from pathlib import Path
import json,hashlib
O=Path(__file__).parent
p=O/'type-shapes.json';j=json.loads(p.read_text())
for r in j['candidates']:
 for k in ['get','set']:
  if r[k]=='-0x140000000':r[k]='0x0'
p.write_text(json.dumps(j,indent=2))
m={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='artifact-manifest.json'}
(O/'artifact-manifest.json').write_text(json.dumps(m,indent=2));print('V7 dispatch artifacts',len(m))
