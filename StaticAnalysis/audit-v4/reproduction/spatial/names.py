exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
for name in ['Position','WorldPosition','WorldTransform','Project','ProjectInner','CameraMatrix','ViewMatrix','Transform']:
 pat=name.encode()+b'\0';poss=[];p=0
 while (p:=pe.d.find(pat,p))>=0:
  if p and pe.d[p-1]!=0:p+=1;continue
  r=pe.rva(p);refs=[];q=0
  while (q:=pe.d.find(struct.pack('<Q',pe.base+r),q))>=0:
   rr=pe.rva(q)
   if rr and 0x4f00000<rr<0x5000000:
    a=q-16;vals=struct.unpack_from('<16Q',pe.d,a);refs.append((hex(rr),[(hex(pe.rva(a+i*8)),hex(v),pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else '') for i,v in enumerate(vals)]))
   q+=1
  if refs:poss.append((hex(r),refs))
  p+=1
 print(name,json.dumps(poss))
for r in [0x4f601c0,0x4f45130]:print(hex(r),[hex(x) for x in pe.unpack('<QQ',r)])
