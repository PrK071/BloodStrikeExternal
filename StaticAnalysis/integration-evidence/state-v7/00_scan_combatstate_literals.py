import hashlib,json,re,struct,sys
from pathlib import Path
import runpy
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal')
EV=ROOT/'StaticAnalysis'/'integration-evidence'
IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf-8'))
assert IDX['index_sha256']=='bb3782da03b95d66451a598add8fe0923405be0dde53a8844b2f8bc107a6ced3'
DEC=runpy.run_path(str(EV/'assets'/'index_script_candidates.py'))['decode_payload']
INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
index=(INSTALL/'Resources.mpkinfo').read_bytes()
assert hashlib.sha256(index).hexdigest()==IDX['index_sha256']
version,count=struct.unpack_from('<II',index); assert version==4 and count==IDX['resource_index_entries']
byidx={r['index']:r for r in IDX['results']}
needles=[b'CombatState',b'gshare.consts',b'ALIVE',b'DYING',b'KNOCKED',b'Enum']
paths_re=re.compile(rb'(?:gshare|gclient|gserver|gcommon|common|client|engine)/[A-Za-z0-9_./-]{1,220}\.py')
input_limit=1_048_576;output_limit=8*1024*1024;aggregate_limit=1024*1024*1024
hits=[];skipped=[];errors=[];total=0;checked=0
with (INSTALL/'Resources.mpk').open('rb') as p0:
    pkgs={0:p0}
    for i in range(count):
        ident,off,size,flags=struct.unpack_from('<QQII',index,8+i*24)
        if flags&1 or size<8: continue
        pkg=flags>>1
        if pkg not in pkgs: pkgs[pkg]=(INSTALL/('Resources'+str(pkg)+'.mpk')).open('rb')
        if size>input_limit:
            skipped.append({'index':i,'size':size,'reason':'input_bound'});continue
        f=pkgs[pkg];f.seek(off);raw=f.read(size)
        if len(raw)!=size: errors.append({'index':i,'reason':'short_read'});continue
        if raw[:2]!=b'\xe2\x06':continue
        checked+=1
        try:
            dec=DEC(raw,output_limit)
            total+=len(dec)
            if total>aggregate_limit: raise RuntimeError('aggregate output cap')
            found=[n.decode() for n in needles if n in dec]
            filepaths=sorted(set(x.decode('ascii') for x in paths_re.findall(dec)))
            if found and ('CombatState' in found or 'gshare.consts' in found):
                row=byidx.get(i)
                ch=hashlib.sha256(raw).hexdigest();dh=hashlib.sha256(dec).hexdigest()
                if row:
                    assert row['compressed_sha256']==ch and row['decoded_sha256']==dh
                hits.append({'index':i,'package':pkg,'opaque_id':hex(ident),'compressed_sha256':ch,'decoded_sha256':dh,'literal_hits':found,'filename_candidates_expanded':filepaths,'known_filename_candidates':row.get('filename_candidates') if row else None,'decoded_size':len(dec)})
        except RuntimeError:raise
        except Exception as e:errors.append({'index':i,'reason':str(e)})
for f in pkgs.values():
    if f is not None:f.close()
out={'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','index_sha256':IDX['index_sha256'],'resource_index_entries':count,'compressed_payloads_checked':checked,'aggregate_decoded_bytes':total,'input_limit':input_limit,'output_limit':output_limit,'aggregate_limit':aggregate_limit,'skipped':skipped,'errors':errors,'literal_hits':hits,'scope':'bounded byte-literal search only; no marshal parse/import/bytecode execution/process access'}
Path(__file__).with_name('00-combatstate-literal-scan.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checked':checked,'bytes':total,'hits':len(hits),'skipped':len(skipped),'errors':len(errors),'matching':[{'index':x['index'],'paths':x['filename_candidates_expanded'],'hits':x['literal_hits']} for x in hits]},indent=2))
