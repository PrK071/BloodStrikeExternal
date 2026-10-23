import json
from pathlib import Path
p=Path(__file__).parent
xs=json.loads((p/'b8-pointer-stores.json').read_text())
for x in xs:
 t=x['store']['text'];r=int(x['store']['rva'],16)
 if 0x200000<r<0xe00000 and '[rbp' not in t and not t.endswith((',rdi',',rsi',',r12',',r13',',r14',',r15')):
  print(x['function'],x['store']['rva'],'\n'+'\n'.join(z['rva']+' '+z['text'] for z in x['around']))
