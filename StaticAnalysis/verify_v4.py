# Python | verify_v4.py | Python 3.12 + iced-x86 + Capstone | disk-only delivery verification.
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from audit_v2 import RawPE, PINNED, save
from iced_x86 import Decoder
sys.path.insert(0,str(Path(__file__).parent/'vendor'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_MEM, X86_OP_IMM, X86_REG_RIP

ROOT=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--sample',type=Path,required=True);a=p.parse_args()
 pe=RawPE(a.sample);assert pe.sha==PINNED
 out=ROOT/'audit-v4';cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 counts=dict(byte_records=0,instruction_records=0,data_records=0);unique={};checked=[]
 def walk(node,key=None):
  if isinstance(node,list):
   for x in node:walk(x)
  elif isinstance(node,dict):
   raw=node.get('bytes');r=node.get('rva',node.get('block_rva'))
   if r is None and isinstance(key,str) and re.fullmatch(r'0x[0-9a-fA-F]+',key):r=key
   if isinstance(raw,str) and isinstance(r,str) and re.fullmatch(r'0x[0-9a-fA-F]+',r):
    data=bytes.fromhex(raw);rva=int(r,16);off=pe.offset(rva,len(data));assert off is not None
    assert pe.d[off:off+len(data)]==data,(current,r)
    if 'file_offset' in node:assert int(node['file_offset'],16)==off,(current,r,'file offset')
    counts['byte_records']+=1
    if 'length' in node and 'text' in node:
     i=Decoder(64,data,ip=pe.base+rva).decode();other=list(cs.disasm(data,pe.base+rva,count=1))
     assert not i.is_invalid and len(other)==1 and i.len==other[0].size==node['length']==len(data),(current,r,'decode')
     if 'rip_target_rva' in node:
      t=int(node['rip_target_rva'],16);assert i.ip_rel_memory_address-pe.base==t
      assert [x.mem.disp+other[0].address+other[0].size-pe.base for x in other[0].operands if x.type==X86_OP_MEM and x.mem.base==X86_REG_RIP]==[t]
     if 'branch_target_rva' in node:
      t=int(node['branch_target_rva'],16);assert i.near_branch_target-pe.base==t
      assert [x.imm-pe.base for x in other[0].operands if x.type==X86_OP_IMM]==[t]
     assert rva not in unique or unique[rva]==data,(current,r,'conflicting bytes')
     unique[rva]=data;counts['instruction_records']+=1
    else:counts['data_records']+=1
   if 'descriptor_bytes' in node:
    data=bytes.fromhex(node['descriptor_bytes']);off=pe.offset(int(node['type_descriptor_rva'],16),len(data))
    assert pe.d[off:off+len(data)]==data
   for k,v in node.items():walk(v,k)
 for current in sorted(out.rglob('*.json')):
  if current.name in ('artifact-sha256.json','delivery-verification.json'):continue
  walk(json.loads(current.read_text(encoding='utf8')));checked.append(str(current.relative_to(ROOT)))
 locked=json.loads((out/'input-lock.json').read_text())
 assert all(sha(ROOT/n)==h for n,h in locked['v3_inputs'].items())
 assert sha(ROOT/'audit-v3/artifact-sha256.json')==locked['v3_manifest_sha256']
 index=json.loads((out/'instruction-index.json').read_text())
 report=(ROOT/'AUDITORIA-V4.md').read_text(encoding='utf8')
 assert all('0x'+x.lower() in index for x in re.findall(r'V4-I-([0-9A-F]+)',report))
 assert len((out/'event-schema.csv').read_text().splitlines())==1
 result=dict(status='PASS_V4_DELIVERY_BYTES',generated_utc=datetime.now(timezone.utc).isoformat(),sample_sha256=pe.sha,
  **counts,unique_code_rvas=len(unique),json_files=len(checked),checked_files=checked,legacy_v3_unchanged=True,
  dynamic_events=0,game_process_access=False,limits='Byte and instruction-length reproduction across selected and discovery artifacts; report semantics and dynamic behavior are not established by this check.')
 save(out/'delivery-verification.json',result)
 files=[ROOT/'AUDITORIA-V4.md',ROOT/'audit_v4.py',ROOT/'discover_v4.py',ROOT/'reproduce_v3_for_v4.py',ROOT/'probe_mpk_v4.py',ROOT/'verify_assets_v4.py',Path(__file__)]
 files+=sorted(f for f in out.rglob('*') if f.is_file() and f.name!='artifact-sha256.json')
 save(out/'artifact-sha256.json',{str(f.relative_to(ROOT)):sha(f) for f in files})
 print(json.dumps({k:v for k,v in result.items() if k!='checked_files'},indent=2))

if __name__=='__main__':main()
