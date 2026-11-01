exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0xdb7870,0xdb7110,0xdb70d0,0xdb7cc0,0x343ef0,0x344340,0x293eb0,0x3ae780]:
 rows=[pe.row(i) for i in pe.decode(r)]
 if not pe.function(r):
  for i,x in enumerate(rows):
   if x['text'].startswith(('ret','jmp ')):rows=rows[:i+1];break
 out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:110]))
(O/'render-camera-link.json').write_text(json.dumps(out,indent=2))
