exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
hier=json.loads((ROOT/'results/rtti-hierarchies.json').read_text());names={'Messiah::MainRenderViewport','Messiah::ClientRenderViewport','Messiah::GenericRenderViewport','Messiah::RenderViewport','Messiah::SceneViewport','Messiah::CameraManagerModule','Messiah::ViewportClient','Messiah::SceneViewportClient'}
types=[];targets=set()
for h in hier:
 if h['name'] not in names:continue
 col=int(h['rva'],16);assert pe.unpack('<I',col)[0]==1
 assert pe.unpack('<I',col+12)[0]==int(h['type_descriptor_rva'],16)
 p=0
 while (p:=pe.d.find(struct.pack('<Q',pe.base+col),p))>=0:
  vr=pe.rva(p)+8;entries=[]
  for i in range(100):
   fn=pe.unpack('<Q',vr+i*8)[0]-pe.base
   if not pe.code(fn):break
   entries.append(dict(slot=hex(i*8),function=hex(fn),region=[hex(x) for x in pe.function(fn)] if pe.function(fn) else None))
  if entries:types.append(dict(hierarchy=h,vtable=hex(vr),entries=entries));targets.add(vr)
  p+=1
refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  if any(x['rva']==hex(r) and x.get('rip_target_rva')==hex(t) for x in rows):refs.append(dict(target=hex(t),instruction=hex(r),region=[hex(x) for x in f],rows=rows));print('init',hex(t),hex(f[0]))
(O/'viewport-types.json').write_text(json.dumps(dict(types=types,refs=refs),indent=2))
for t in types:print(t['hierarchy']['name'],t['vtable'],[(x['slot'],x['function']) for x in t['entries']])
