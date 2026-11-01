exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x493c00,0x4876a0,0x485230,0x493650,0x4850a0,0x4b0190,0x4b3ac0,0x493c40]:
 rows=[pe.row(i) for i in pe.decode(r)]
 if not pe.function(r):
  for i,x in enumerate(rows):
   if x['text'].startswith(('ret','jmp ')):rows=rows[:i+1];break
 out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:90]))
(O/'projection-storage.json').write_text(json.dumps(out,indent=2))
