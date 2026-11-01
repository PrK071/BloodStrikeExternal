exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0xdb73c0,0xdb73d0,0xdb7b98,0x678c20,0xc46ca0,0xdb7710,0xdb8110,0xdb8130,0x329110]:
 rows=[pe.row(i) for i in pe.decode(r)]
 if not pe.function(r):
  for i,x in enumerate(rows):
   if x['text'].startswith(('ret','jmp ')):rows=rows[:i+1];break
 out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:90]))
(O/'pipeline-consumer.json').write_text(json.dumps(out,indent=2))
