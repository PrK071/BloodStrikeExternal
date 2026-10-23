exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
from iced_x86 import Decoder
out=out/'render-source';targets={0x80f6dc8,0x80f69c1};refs=[];candidates=[];cache={}
import re
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',b,re.S):
  r=s['rva']+m.start();t=r+6+struct.unpack_from('<i',b,m.start()+2)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  if f[0] not in cache:cache[f[0]]=[pe.row(i) for i in pe.decode(f[0])]
  row=next((x for x in cache[f[0]] if int(x['rva'],16)<=r<int(x['rva'],16)+x['length']),None)
  refs.append({'target':hex(t),'function':hex(f[0]),'instruction':row})
 # All exact disp32 fa0 code candidates, validated instruction boundaries from unwind
 p=0
 while (p:=b.find(b'\xa0\x0f\x00\x00',p))>=0:
  r=s['rva']+p;f=pe.function(r)
  if f:
   if f[0] not in cache:cache[f[0]]=[pe.row(i) for i in pe.decode(f[0])]
   row=next((x for x in cache[f[0]] if int(x['rva'],16)<=r<int(x['rva'],16)+x['length']),None)
   if row and '0FA0h' in row['text']:candidates.append({'function':hex(f[0]),'instruction':row})
  p+=1
(out/'registry-refs.json').write_text(json.dumps(refs,indent=2));(out/'fa0-candidates.json').write_text(json.dumps(candidates,indent=2));(out/'candidate-functions.json').write_text(json.dumps({hex(k):v for k,v in cache.items()},indent=2));print('REFS',json.dumps(refs));print('FA0',json.dumps(candidates))
