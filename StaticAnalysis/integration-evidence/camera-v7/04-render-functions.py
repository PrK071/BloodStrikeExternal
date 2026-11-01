exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x314c250,0x1991160,0x9523a0,0x2311810,0x23306e0,0x23471a0]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:90]))
out['strings']={hex(r):pe.string(r) for r in [0x4f9db78,0x4ea5c68,0x4e4ac60]}
(O/'render-functions.json').write_text(json.dumps(out,indent=2));print(out['strings'])
