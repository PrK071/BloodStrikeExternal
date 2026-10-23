# Python | v4_scan.py | Python 3.12 + iced-x86 | disk-only discovery for V4.
import sys,json,time
from pathlib import Path
root=Path(__file__).parent
sys.path.insert(0,str(root))
from audit_v2 import RawPE,PINNED,save
from iced_x86 import Decoder,OpKind,FlowControl
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha==PINNED
targets={int(x,16) for x in '''79602f0 115eb00 16d0e70 19bfe20 19bfed0 19c0100
8b7cd90 19d45e0 10ea20 10e3f0 10eaa0 80cfff0 8e45608 2d845b0 899eb0 2d82b80 3f3950'''.split()}
refs=[];near=[];count=0;invalid=0;started=time.perf_counter()
for j,(b,e,u) in enumerate(pe.functions):
 off=pe.offset(b,e-b)
 for ins in Decoder(64,pe.d[off:off+e-b],ip=pe.base+b):
  count+=1
  if ins.is_invalid:invalid+=1;continue
  t=None
  if ins.is_ip_rel_memory_operand:
   t=ins.ip_rel_memory_address-pe.base
   if 0x79602c0<=t<0x7960330:near.append(dict(runtime_rva=hex(b),instruction=pe.row(ins)))
  elif ins.flow_control in (FlowControl.CALL,FlowControl.UNCONDITIONAL_BRANCH,FlowControl.CONDITIONAL_BRANCH) and ins.op0_kind in (OpKind.NEAR_BRANCH16,OpKind.NEAR_BRANCH32,OpKind.NEAR_BRANCH64):t=ins.near_branch_target-pe.base
  if t in targets:refs.append(dict(target_rva=hex(t),runtime_rva=hex(b),instruction=pe.row(ins)))
 if j and j%100000==0:print('records',j,flush=True)
data=[]
for r in pe.relocations:
 t=pe.unpack('<Q',r)[0]-pe.base
 if t in targets:data.append(dict(slot_rva=hex(r),target_rva=hex(t)))
result=dict(sha256=pe.sha,records=len(pe.functions),decoded=count,invalid=invalid,seconds=time.perf_counter()-started,
 references=refs,counter_near_references=near,relocated_pointers=data,scope='Linear decode in unwind records; selected CFG confirmation required; leaf and computed references incomplete.')
save(root/'audit-v4/discovery.json',result)
summary={hex(t):sum(x['target_rva']==hex(t) for x in refs) for t in targets}
print(json.dumps(summary,indent=2),flush=True)
for x in refs:
 if x['target_rva'] in ('0x79602f0','0x115eb00','0x16d0e70','0x19bfe20','0x10ea20','0x8e45608'):print(x['target_rva'],x['runtime_rva'],x['instruction']['rva'],x['instruction']['text'])
