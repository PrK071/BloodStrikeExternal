# Python | trace_parent_state.py | Python 3.12, iced-x86 and Capstone | pinned PE, disk only.
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,cfg,save
sys.path.insert(0,str(ROOT/'vendor'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

def main():
 pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'))
 assert pe.sha==PINNED
 out=Path(__file__).parent
 locked=json.loads((ROOT/'audit-v4/artifact-sha256.json').read_text())
 assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in locked.items())
 table=0x4e93470;index=0x5b;slot=table+index*8
 token=pe.unpack('<Q',slot)[0]-pe.base
 string=pe.unpack('<Q',token)[0]-pe.base
 assert (slot,token,string)==(0x4e93748,0x4e71948,0x4e9d9d8)
 assert pe.string(string)=='IsInWorld'
 data=[]
 for label,r,n in [('INT-P-D01',slot,8),('INT-P-D02',token,24),('INT-P-D03',string,10),('INT-P-D04',0x4f64210,0x100)]:
  off=pe.offset(r,n);data.append(dict(id=label,rva=hex(r),file_offset=hex(off),bytes=pe.d[off:off+n].hex(' ')))
 graphs=[dict(label=name,**cfg(pe,r,10000,0x100000)) for name,r in [
  ('interned_token_select',0x470dc0),('token_to_lookup_key',0x470ff0),('association',0x19c0100),
  ('is_in_world_getter',0x952640),('activation',0x19d4b00),('deactivation',0x19d4eb0),('get_all_actors',0x3259770)]]
 cs=Cs(CS_ARCH_X86,CS_MODE_64);count=0
 for graph in graphs:
  assert not graph['capped']
  for row in graph['instructions']:
   raw=bytes.fromhex(row['bytes']);other=list(cs.disasm(raw,int(row['preferred_va'],16),count=1))
   assert len(other)==1 and other[0].size==row['length']
   row['evidence_id']='INT-P-I-'+row['rva'][2:].upper();count+=1
 save(out/'data.json',data);save(out/'code.json',graphs)
 save(out/'summary.json',dict(status='PASS_PARENT_STATE_TOKEN',sha256=pe.sha,table_rva=hex(table),token_index=hex(index),
  token_pointer_slot_rva=hex(slot),token_rva=hex(token),string_rva=hex(string),text=pe.string(string),cfg_entries=len(graphs),
  instruction_records=count,v4_inputs_unchanged=True,process_access=False,
  scope='Static token selection and association CFG; no runtime type, registration outcome or concurrency observation.'))
 print(json.dumps(dict(status='PASS_PARENT_STATE_TOKEN',token_index=hex(index),text=pe.string(string),instruction_records=count)))

if __name__=='__main__':main()
