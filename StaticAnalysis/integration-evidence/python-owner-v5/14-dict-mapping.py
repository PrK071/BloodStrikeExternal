exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r,n in [(0x7a19900,0x1b0),(0x7a198c0,0x40)]:
 rows=[]
 for k in range(0,n,8):
  v=pe.unpack('<Q',r+k)[0];rows.append(dict(offset=hex(k),value=hex(v),string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None))
 out[hex(r)]=rows
m=pe.unpack('<Q',0x7a19900+0x70)[0]-pe.base;print('mapping',hex(m))
for k in [0,8,16]:
 v=pe.unpack('<Q',m+k)[0];print('slot',k,hex(v-pe.base))
rows=[pe.row(i) for i in pe.decode(pe.unpack('<Q',m+8)[0]-pe.base)];out['mapping_subscript']=rows
print('\n'.join(x['rva']+' '+x['text'] for x in rows[:100]));(O/'dict-type-mapping.json').write_text(json.dumps(out,indent=2))
