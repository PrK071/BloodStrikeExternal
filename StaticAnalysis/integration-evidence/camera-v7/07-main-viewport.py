exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0xdb8c90,0xdb8500,0xdb85d0,0xdb85f0,0xdb8590,0xdb8550,0xdb8570,0xdb7ac0,0xdb7c60,0xdb83a0,0xdb8620,0xdb7f30]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:100]))
(O/'main-viewport-functions.json').write_text(json.dumps(out,indent=2))
