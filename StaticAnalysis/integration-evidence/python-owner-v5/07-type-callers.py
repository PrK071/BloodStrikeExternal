exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
import re,struct
O=Path(__file__).parent;out=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'\xe8.{4}',data,re.S):
  r=s['rva']+m.start();t=r+5+struct.unpack_from('<i',m.group(),1)[0]
  if t!=0x2052480:continue
  f=pe.function(r)
  if not f:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  if not any(x['rva']==hex(r) and x.get('branch_target_rva')==hex(t) for x in rows):continue
  out.append(dict(function=hex(f[0]),call_rva=hex(r),rows=rows));print(hex(f[0]),len(rows));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:45]))
(O/'entity-type-callers.json').write_text(json.dumps(out,indent=2))
