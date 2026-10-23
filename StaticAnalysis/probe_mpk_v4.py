# Python | probe_mpk_v4.py | Python 3.12 | disk-only candidate MPKINFO layout validation.
"""Test a candidate layout; never extract, decrypt or execute packaged files."""
import argparse, collections, hashlib, json, struct
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--install',type=Path,required=True);a=p.parse_args()
 results=[]
 for name in ('Engine','Resources'):
  f=a.install/(name+'.mpkinfo');raw=f.read_bytes();version,count=struct.unpack_from('<II',raw)
  result=dict(path=str(f),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),first_u32=version,count_candidate=count,
   hypothesis='8-byte header; count records <QQII: opaque identifier, offset, size, flags; low flag bit directory, other bits package index; unclassified trailer')
  if version!=4 or count>(len(raw)-8)//24:
   result['status']='INCOMPATIBLE_CANDIDATE';results.append(result);continue
  rows=[];issues=[];flags=collections.Counter();magics=collections.Counter();samples=[];sizes={}
  for j in range(count):
   ident,offset,size,flag=struct.unpack_from('<QQII',raw,8+j*24);flags[flag]+=1
   directory=bool(flag&1);package=flag>>1;data=a.install/(name+('' if package==0 else str(package))+'.mpk')
   if data not in sizes:sizes[data]=data.stat().st_size if data.is_file() else None
   if not directory and (sizes[data] is None or offset+size>sizes[data]):issues.append(dict(index=j,package=package,offset=offset,size=size,available=sizes[data]))
   row=dict(index=j,opaque_id=hex(ident),offset=offset,size=size,flags=flag,directory_candidate=directory,package_candidate=package)
   if j<12 or (name=='Resources' and j%2000==0):
    if not directory and sizes[data] is not None and offset+size<=sizes[data] and size:
     with data.open('rb') as h:h.seek(offset);head=h.read(min(size,32))
     row['payload_head']=head.hex(' ');magics[head[:4].hex()]+=1
    samples.append(row)
  trailer=raw[8+24*count:]
  result.update(status='CANDIDATE_BOUNDS_PASS' if not issues else 'CANDIDATE_BOUNDS_FAIL',
   directory_candidates=sum(v for k,v in flags.items() if k&1),flags_histogram=dict(flags),
   package_sizes={str(k):v for k,v in sizes.items()},bounds_failures=issues,
   trailer_hex=trailer.hex(' '),trailer_bytes=len(trailer),payload_magic_histogram=dict(magics),samples=samples,
   limitations='Bounds consistency is not proof of field meaning, ID hashing, compression, directory semantics or compatibility with patch index.')
  results.append(result)
 out=Path(__file__).parent/'audit-v4/mpk-candidate-probe.json';out.write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps([{k:r[k] for k in ('path','status','count_candidate','trailer_bytes','directory_candidates') if k in r} for r in results],indent=2))

if __name__=='__main__':main()
