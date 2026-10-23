# Python 3.12 | ClientPlayer field-owner methods and vtable slots.
"""Inspect static ClientPlayer constructor/destructor/vtable methods for the Char field."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,cfg

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 chain=json.loads((Path(__file__).parent.parent/'chain-evidence.json').read_text(encoding='utf-8'))
 starts={0xa76b40,0xa77290,0xacc650}
 vt=[]
 for x in chain['rtti_vftable_candidates']:
  if x['name']!='Messiah::ClientPlayer':continue
  for v in x['candidate_vftables']:
   vt.append({'vtable_rva':v['vtable_rva'],'slots':v['slots']})
   starts.update(int(s['target_rva'],16) for s in v['slots'])
 functions=[]
 for start in sorted(starts):
  f=pe.function(start);ins=pe.decode(start,65536);rows=[pe.row(i) for i in ins]
  graph=cfg(pe,start,max_instructions=800,span=0x8000)
  field_hits=[r for r in rows if any(term in r['text'].lower() for term in ['0ea0h','0ec0h','0ea0','0ec0'])]
  functions.append({'entry_rva':hex(start),'runtime_function':[hex(v) for v in f] if f else None,'instruction_count':len(rows),'field_offset_instruction_hits':field_hits,'instructions':rows[:100],'bounded_cfg':graph})
 out={'sha256':pe.sha,'clientplayer_vtables':vt,'constructor_destructor_and_virtuals':functions,'field_offset_hypothesis':{'char_property_accessor_candidate':'0xce4570','candidate_displacement':'0xea0','second adjacent accessor candidate':'0x6a5850','candidate_displacement_2':'0xec0'},'limits':['Vtable slot names are not symbols; first entry is not automatically a destructor without confirming control flow.','Only direct CFG edges followed; callees and indirect calls omitted.','A field offset accessor returns an address and does not by itself reveal pointee/type.']}
 dest=Path(__file__).parent/'04-clientplayer-methods.json';dest.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
 print(json.dumps({'sha256':pe.sha,'virtual_targets':len(starts),'field_hits':sum(len(f['field_offset_instruction_hits']) for f in functions),'output':str(dest)},indent=2))
if __name__=='__main__':main()
