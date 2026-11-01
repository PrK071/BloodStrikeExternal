from pathlib import Path
import hashlib,json
O=Path(__file__).parent
m={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='artifact-manifest.json'}
(O/'artifact-manifest.json').write_text(json.dumps(m,indent=2));print('managed evidence files',len(m))
