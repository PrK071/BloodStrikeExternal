exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x2da2f0,0x293660,0x2936e0,0x293980,0x293460,0x3afcf0,0x293990,0x343040,0x343ef0]:
 rows=[pe.row(i) for i in pe.decode(r)]
 if not pe.function(r):
  for i,x in enumerate(rows):
   if x['text'].startswith(('ret','jmp ')):rows=rows[:i+1];break
 out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:150]))
(O/'viewport-client-selector.json').write_text(json.dumps(out,indent=2))
