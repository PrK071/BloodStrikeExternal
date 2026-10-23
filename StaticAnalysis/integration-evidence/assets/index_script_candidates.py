# Python | index_script_candidates.py | Python 3.12 standard library | bounded static resource metadata indexing.
import argparse,contextlib,hashlib,json,re,struct,time,zlib
from pathlib import Path
OUT=Path(__file__).parent
INDEX_HASH='bb3782da03b95d66451a598add8fe0923405be0dde53a8844b2f8bc107a6ced3'
TERMS=[b'ActorComponent',b'GetAllActors',b'IsInWorld',b'LocalPlayer',b'PlayerController',b'SpikePlayer',b'SpikeSpellWorker',
 b'CharacterController',b'SpellWorker',b'GetMainCamera',b'ViewMatrix',b'WorldPosition',b'TeamId',b'team_id',b'health',b'enemy']

def decode_payload(raw,limit):
 n=len(raw);assert n>=8 and raw[:2]==b'\xe2\x06'
 b=bytearray(raw);prefix=min(128-((n-8)%37),n)
 for i in range(prefix):b[i]^=0x9a
 end=n if prefix==n else n-8
 decoder=zlib.decompressobj();value=decoder.decompress(bytes(b[:end]),limit+1)
 if len(value)>limit or not decoder.eof or decoder.unconsumed_tail:raise ValueError('output bound or incomplete zlib')
 if decoder.unused_data:raise ValueError('unexpected bytes after zlib stream')
 return value

def read_entry(install,index,i):
 ident,off,size,flags=struct.unpack_from('<QQII',index,8+i*24)
 path=install/('Resources'+('' if flags>>1==0 else str(flags>>1))+'.mpk')
 with path.open('rb') as h:h.seek(off);raw=h.read(size)
 if len(raw)!=size:raise ValueError('short payload read')
 return raw,dict(index=i,opaque_id=hex(ident),package=flags>>1,offset=off,size=size)

def main():
 p=argparse.ArgumentParser();p.add_argument('--install',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE'))
 p.add_argument('--input-limit',type=int,default=1048576);p.add_argument('--output-limit',type=int,default=8*1048576)
 p.add_argument('--aggregate-limit',type=int,default=1024*1048576);a=p.parse_args()
 index=(a.install/'Resources.mpkinfo').read_bytes();assert hashlib.sha256(index).hexdigest()==INDEX_HASH
 version,count=struct.unpack_from('<II',index);assert version==4 and len(index)==8+24*count+16
 results=[];errors=[];skipped=[];aggregate=0;begin=time.perf_counter()
 with contextlib.ExitStack() as stack:
  packages={};entries=[]
  for i in range(count):
   ident,off,n,flags=struct.unpack_from('<QQII',index,8+i*24)
   if flags&1 or n<2:continue
   pkg=flags>>1
   if pkg not in packages:packages[pkg]=stack.enter_context((a.install/('Resources'+('' if pkg==0 else str(pkg))+'.mpk')).open('rb'))
   entries.append((pkg,off,i,ident,n))
  for pkg,off,i,ident,n in sorted(entries):
   f=packages[pkg];f.seek(off)
   if f.read(2)!=b'\xe2\x06':continue
   info=dict(index=i,opaque_id=hex(ident),package=pkg,offset=off,size=n)
   if n>a.input_limit:skipped.append(dict(**info,reason='input_bound'));continue
   f.seek(off);raw=f.read(n);assert len(raw)==n
   try:
    value=decode_payload(raw,a.output_limit);aggregate+=len(value)
    if aggregate>a.aggregate_limit:raise RuntimeError('aggregate output bound reached')
    paths=sorted(set(x.decode('ascii') for x in re.findall(rb'(?:gclient|gserver|gcommon|common|client|engine)/[A-Za-z0-9_./-]{1,220}\.py',value)))
    results.append(dict(**info,compressed_sha256=hashlib.sha256(raw).hexdigest(),decoded_sha256=hashlib.sha256(value).hexdigest(),
     decoded_size=len(value),decoded_head=value[:16].hex(' '),filename_candidates=paths,
     literal_hits={x.decode('ascii'):value.count(x) for x in TERMS if x in value}))
   except RuntimeError:raise
   except Exception as e:errors.append(dict(**info,error=str(e)))
 results.sort(key=lambda x:x['index'])
 result=dict(index_sha256=INDEX_HASH,status='INDEX_COMPLETE_WITH_DECLARED_BOUNDS',resource_index_entries=count,decoded_entries=len(results),
  aggregate_decoded_bytes=aggregate,seconds=time.perf_counter()-begin,raw_tree_extracted=False,bytecode_executed=False,
  input_limit=a.input_limit,output_limit=a.output_limit,aggregate_limit=a.aggregate_limit,skipped=skipped,errors=errors,
  results=results,limits='Paths and symbol counts are literal candidates, not parsed code attributes, type classification or proof of calls. Resource overlay freshness not established.')
 (OUT/'script-candidate-index.json').write_text(json.dumps(result,indent=2)+'\n')
 prioritized=[x for x in results if any(k in x['literal_hits'] for k in ['GetAllActors','ActorComponent','LocalPlayer','SpikePlayer','PlayerController'])]
 print(json.dumps(dict(decoded=len(results),bytes=aggregate,errors=len(errors),skipped=len(skipped),prioritized_count=len(prioritized),
  prioritized=[{k:x[k] for k in ['index','filename_candidates','literal_hits']} for x in prioritized][:35]),indent=2))

if __name__=='__main__':main()
