# Python 3.12 | static bounded code/data windows using audit_v2.RawPE.
"""Trace selected RTTI vtable references and reflected metadata pointer slots."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 source=json.loads((Path(__file__).parent/'chain-evidence.json').read_text(encoding='utf-8'))
 out={'binary_sha256':pe.sha,'function_windows':[],'metadata_windows':[],'limits':['Windows are static bytes decoded with audit_v2.RawPE; no target execution or process access.','Unlabeled methods remain unnamed even when vtable-linked.']}
 starts=[0xa76b40,0xa77290,0x19bf520,0x19bf730,0x19bf960,0x19bfb60]
 for start in starts:
  f=pe.function(start);ins=pe.decode(start,65536);rows=[pe.row(i) for i in ins]
  out['function_windows'].append({'start_rva':hex(start),'runtime_function':[hex(v) for v in f] if f else None,'instruction_count':len(rows),'instructions':rows[:120]})
 for ref in source['references']:
  if ref['kind']!='data_pointer' or not ref['target'].startswith('string '):continue
  r=int(ref['rva'],16);o=pe.offset(r)
  lo=max(0,o-64);hi=min(len(pe.d),o+72)
  ptrs=[]
  for po in range(max(0,o-64)//8*8,min(len(pe.d),o+72),8):
   v=struct.unpack_from('<Q',pe.d,po)[0];target=v-pe.base
   if pe.code(target) or pe.section(target): ptrs.append({'file_offset':hex(po),'rva':hex(pe.rva(po)),'value':hex(v),'target_rva':hex(target),'target_is_code':pe.code(target),'target_string':pe.string(target)})
  out['metadata_windows'].append({'label':ref['target'],'string_rva':ref['target_rva'],'pointer_slot_rva':ref['rva'],'pointer_slot_bytes':pe.d[o:o+8].hex(' '),'window_file_offset':hex(lo),'window_rva':hex(pe.rva(lo)),'window_hex':pe.d[lo:hi].hex(' '),'pointer_like_values':ptrs})
 dest=Path(__file__).parent/'trace-evidence.json';dest.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
 print(json.dumps({'sha256':pe.sha,'function_windows':len(out['function_windows']),'metadata_windows':len(out['metadata_windows']),'output':str(dest)},indent=2))
if __name__=='__main__':main()
