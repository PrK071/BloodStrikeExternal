from pathlib import Path
import json,hashlib
O=Path(__file__).parent;j=json.loads((O/'screenpoint-callers-static.json').read_text());select={'CommonTopLogo._UpdateMarkToplogo','CommonTopLogo.GetScreenPointFromWorldPointPython','UIDirector.WorldToScreen','MarkTopLogo._UpdateMarkToplogo','MarkTopLogo.GetScreenPointFromWorldPointPython'}
rs=[dict(index=r['index'],decoded_sha256=r['decoded_sha256'],codes=[c for c in r['codes'] if c['qualname'] in select]) for r in j];rs=[r for r in rs if r['codes']]
(O/'screenpoint-callers-selected.json').write_text(json.dumps(rs,indent=2))
(O/'manifest.json').write_text(json.dumps(dict(target_sha256='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747',target_executed=False,bytecode_executed=False,files=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size) for p in sorted(O.iterdir()) if p.is_file() and p.name!='manifest.json']),indent=2))
print([(r['index'],[c['qualname'] for c in r['codes']]) for r in rs])
