exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
import re
out=out/'projection';targets={0x5ba6f28,0x55aef10};refs=[];cache={}
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',b,re.S):
  r=s['rva']+m.start();target=r+6+struct.unpack_from('<i',b,m.start()+2)[0]
  if target not in targets:continue
  f=pe.function(r)
  if not f:refs.append({'candidate':hex(r),'target':hex(target),'unwind':False});continue
  if f[0] not in cache:cache[f[0]]=[pe.row(i) for i in pe.decode(f[0])]
  row=next((x for x in cache[f[0]] if int(x['rva'],16)<=r<int(x['rva'],16)+x['length']),None)
  refs.append({'target':hex(target),'function':hex(f[0]),'instruction':row})
(out/'rip-refs.json').write_text(json.dumps(refs,indent=2));(out/'ref-functions.json').write_text(json.dumps({hex(k):v for k,v in cache.items()},indent=2));print(json.dumps(refs,indent=2))


