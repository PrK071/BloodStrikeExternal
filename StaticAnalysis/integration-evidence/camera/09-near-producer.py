import json
from pathlib import Path
xs=json.loads((Path(__file__).parent/'b8-pointer-stores.json').read_text())
for x in xs:
 if x['function'] in ['0xc43fb0','0xc562d0','0xc56500','0xc57650','0xc579f0','0xc610d0','0x7823b0']:
  print('\n',x['function']);print('\n'.join(z['rva']+' '+z['text'] for z in x['around']))
