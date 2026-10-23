# Python | v4_integrity.py | Python 3.12, iced-x86 and Capstone | disk-only V3 reproduction.
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).parent
sys.path.insert(0,str(root))
from audit_v2 import RawPE,PINNED,save
sys.path.insert(0,str(root/'vendor'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
from iced_x86 import Decoder
out=root/'audit-v4';out.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'RUNNING','runtime_game_access':False};save(out/'v3-reproduction.json',result)
try:
 manifest=json.loads((root/'audit-v3/artifact-sha256.json').read_text())
 checks=[dict(path=n,expected=h,actual=sha(root/n)) for n,h in manifest.items()]
 assert all(c['expected']==c['actual'] for c in checks)
 pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'))
 assert pe.sha==PINNED
 graphs=json.loads((root/'audit-v3/reachable-code.json').read_text())
 rows={r['rva']:r for g in graphs for r in g['instructions']};cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 rip=branch=0
 for r in rows.values():
  addr=int(r['rva'],16);raw=bytes.fromhex(r['bytes']);off=pe.offset(addr,len(raw));assert off==int(r['file_offset'],16)
  actual=pe.d[off:off+len(raw)];assert actual==raw
  ins=Decoder(64,actual,ip=pe.base+addr).decode();other=list(cs.disasm(actual,pe.base+addr,count=1))
  assert not ins.is_invalid and ins.len==r['length']==other[0].size
  if 'rip_target_rva' in r:
   expected=int(r['rip_target_rva'],16)
   assert ins.ip_rel_memory_address-pe.base==expected
   assert [o.mem.disp+other[0].address+other[0].size-pe.base for o in other[0].operands if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP]==[expected];rip+=1
  if 'branch_target_rva' in r:
   expected=int(r['branch_target_rva'],16)
   assert ins.near_branch_target-pe.base==expected
   assert [o.imm-pe.base for o in other[0].operands if o.type==X86_OP_IMM]==[expected];branch+=1
 data=json.loads((root/'audit-v3/data-evidence.json').read_text())
 for d in data:
  raw=bytes.fromhex(d['bytes']);off=pe.offset(int(d['rva'],16),len(raw));assert pe.d[off:off+len(raw)]==raw
 locked=json.loads((root/'audit-v3/baseline-lock.json').read_text())
 assert all(sha(root/n)==h for n,h in locked['input_sha256'].items())
 result=dict(status='PASS_V3_REPRODUCED',generated_utc=datetime.now(timezone.utc).isoformat(),sha256=pe.sha,
  v3_manifest_sha256=sha(root/'audit-v3/artifact-sha256.json'),manifest_checks=checks,unique_instructions=len(rows),
  rip_targets=rip,branch_targets=branch,data_blocks=len(data),v2_and_legacy_inputs_unchanged=True,runtime_game_access=False,
  scope='Re-read pinned sample, all V3 manifest entries, selected instruction bytes/lengths/targets with both decoders, all V3 data snapshots; no semantic or runtime equivalence assumed.')
 save(out/'v3-reproduction.json',result);print(json.dumps({k:v for k,v in result.items() if k!='manifest_checks'},indent=2))
except Exception as exc:
 save(out/'v3-reproduction.json',dict(status='FAIL',error=repr(exc),runtime_game_access=False));raise
