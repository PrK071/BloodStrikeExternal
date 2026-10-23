exec((__import__('pathlib').Path(__file__).parent/'01-callers.py').read_text().split('res=[]')[0])
q=0x4e549c0
while pe.code(pe.unpack('<Q',q-8)[0]-pe.base):q-=8
v=pe.unpack('<Q',q-8)[0]-pe.base
print('TABLE',hex(q),'SLOT',hex(0x4e549c0-q),'COL',hex(v))
try:
 td=pe.unpack('<I',v+12)[0];print('TYPE',hex(td),pe.string(td+16))
except:pass
for i in range(0,0xb8,8):print(hex(q+i),hex(pe.unpack('<Q',q+i)[0]-pe.base))
# RIP code refs for entries/table.
res=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',b,re.S):
  r=s['rva']+m.start();t=r+6+struct.unpack_from('<i',b,m.start()+2)[0]
  if t not in [q,0xc46ca0]:continue
  f=pe.function(r)
  if f:
   rr=rows(f[0]);i=next((i for i,x in enumerate(rr) if int(x['rva'],16)<=r<int(x['rva'],16)+x['length']),None)
   if i is not None:res.append({'target':hex(t),'function':hex(f[0]),'around':rr[max(0,i-12):i+15]})
save('entry-rip-addresses.json',res);save('entry-rip-functions.json',{hex(k):v for k,v in cache.items()});print(json.dumps(res))
