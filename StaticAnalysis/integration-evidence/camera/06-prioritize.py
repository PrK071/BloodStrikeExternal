import json,re
from pathlib import Path
p=Path(__file__).parent;xs=json.loads((p/'b8-pointer-stores.json').read_text());res=[]
for x in xs:
 t=x['store']['text'];src=t.split(',')[-1];ar=x['around'];idx=next(i for i,z in enumerate(ar) if z['rva']==x['store']['rva']);prev=ar[:idx]
 if '[rbp' in t or '[rsp' in t:continue
 defs=[z for z in prev if z['text'].startswith('mov '+src+',')]
 if defs and any(v in defs[-1]['text'] for v in ['+8]','+0DC0h]','+0DD0h]','+218h]','+30h]']):res.append(x)
(p/'b8-prioritized-load-stores.json').write_text(json.dumps(res,indent=2));print('COUNT',len(res))
for x in res:print(x['function'],x['store']['rva'],' | '.join(z['text'] for z in x['around'][-8:]))
