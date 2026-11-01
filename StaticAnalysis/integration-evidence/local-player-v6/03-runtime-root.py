exec((__import__('pathlib').Path(__file__).parent/'01-runtime-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(b'\xe8',data):
  r=s['rva']+m.start()
  if m.start()+5>len(data) or r+5+struct.unpack_from('<i',data,m.start()+1)[0]!=0x2addac0:continue
  f=pe.function(r)
  if not f:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  if not any(x['rva']==hex(r) and x.get('branch_target_rva')=='0x2addac0' for x in rows):continue
  refs.append(dict(call=hex(r),function=hex(f[0]),rows=rows))
  print(hex(f[0]));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:120]))
cookies=[];p=0
while (p:=pe.d.find(b'xdebugpy',p))>=0:
 r=pe.rva(p);cookies.append(dict(rva=hex(r),file_offset=hex(p),qwords=[hex(v) for v in pe.unpack('<96Q',r)]));p+=1
(O/'runtime-root.json').write_text(json.dumps(dict(refs=refs,cookies=cookies),indent=2))
print('cookies',[(x['rva'],x['qwords'][:16]) for x in cookies])
