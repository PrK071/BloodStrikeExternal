import json
from pathlib import Path
xs=json.loads((Path(__file__).parent/'b8-pointer-stores.json').read_text())
res=[x for x in xs if 0x400000<int(x['store']['rva'],16)<0xc80000 and '[rbp' not in x['store']['text'] and '[rsp' not in x['store']['text']]
print('COUNT',len(res))
for x in res: print(x['function'],x['store']['rva'],x['store']['text'])
