import hashlib,json,re,struct,runpy
from pathlib import Path
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal');EV=ROOT/'StaticAnalysis'/'integration-evidence';IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf-8'))
DEC=runpy.run_path(str(EV/'assets'/'index_script_candidates.py'))['decode_payload'];INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE');index=(INSTALL/'Resources.mpkinfo').read_bytes();assert hashlib.sha256(index).hexdigest()==IDX['index_sha256'];version,count=struct.unpack_from('<II',index);assert version==4
byidx={x['index']:x for x in IDX['results']}; pat=re.compile(rb'(?:gshare|gclient|gserver|gcommon|common|client|engine)/[A-Za-z0-9_./-]{1,220}\.py')
lim_in=1048576;lim_out=8*1024*1024;lim_total=1024*1024*1024;total=0;checked=0;matches=[];skip=[];errs=[];pkgs={}
with (INSTALL/'Resources.mpk').open('rb') as f0:
 pkgs[0]=f0
 for i in range(count):
  ident,off,size,flags=struct.unpack_from('<QQII',index,8+i*24)
  if flags&1 or size<8:continue
  pkg=flags>>1
  if pkg not in pkgs: pkgs[pkg]=(INSTALL/('Resources'+str(pkg)+'.mpk')).open('rb')
  if size>lim_in:skip.append(i);continue
  f=pkgs[pkg];f.seek(off);raw=f.read(size)
  if len(raw)!=size or raw[:2]!=b'\xe2\x06':continue
  checked+=1
  try:
   b=DEC(raw,lim_out);total+=len(b)
   if total>lim_total:raise RuntimeError('total limit')
   paths=sorted(set(x.decode('ascii') for x in pat.findall(b)))
   if 'gshare/utils.py' in paths:
    row=byidx.get(i);ch=hashlib.sha256(raw).hexdigest();dh=hashlib.sha256(b).hexdigest()
    if row:assert (ch,dh)==(row['compressed_sha256'],row['decoded_sha256'])
    matches.append({'index':i,'package':pkg,'opaque_id':hex(ident),'compressed_sha256':ch,'decoded_sha256':dh,'size':len(b),'has_enum_word':b'enum' in b,'has_Enum_word':b'Enum' in b,'has_IntEnum':b'IntEnum' in b,'has_enum_function':b'def enum' in b,'known_paths':row.get('filename_candidates') if row else None})
  except RuntimeError:raise
  except Exception as e:errs.append({'index':i,'error':str(e)})
for f in pkgs.values():f.close()
out={'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','index_sha256':IDX['index_sha256'],'checked':checked,'total_decoded_bytes':total,'input_limit':lim_in,'output_limit':lim_out,'total_limit':lim_total,'skipped_input_limit':skip,'errors':errs,'matches':matches,'scope':'bounded literal path scan; no parsing/execution/import/process access'}
Path(__file__).with_name('02-scan-enum-factory.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checked':checked,'bytes':total,'matches':matches,'skip':len(skip),'errors':len(errs)},indent=2))
