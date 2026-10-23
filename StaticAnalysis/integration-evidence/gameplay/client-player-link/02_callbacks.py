# Python 3.12 | Static callback CFGs for reflected ClientPlayer.Char metadata.
"""Decode metadata-adjacent native callbacks using RawPE and bounded direct-CFG walks."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,cfg

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 source=json.loads((Path(__file__).parent/'01-link-probe.json').read_text(encoding='utf-8'))
 starts=set()
 for w in source['data_pointer_windows']:
  if w['property']!='Messiah.ClientPlayer.Char':continue
  for q in w['pointers']:
   if q['target_code']:starts.add(int(q['target_rva'],16))
 rows=[]
 for start in sorted(starts):
  f=pe.function(start);ins=pe.decode(start,16384);raw=[pe.row(i) for i in ins[:64]]
  graph=cfg(pe,start,max_instructions=128,span=0x1000)
  rows.append({'entry_rva':hex(start),'runtime_function':[hex(x) for x in f] if f else None,'linear_instructions':raw,'linear_truncated':len(ins)>len(raw),'bounded_cfg':graph,'cfg_instruction_count':len(graph['instructions'])})
 out={'binary_sha256':pe.sha,'rtti_hierarchies_sha256':source['rtti_hierarchies_sha256'],'metadata_pointer_windows':['0x51e4600','0x51f9170','0x51f9190'],'unique_code_targets':len(starts),'callbacks':rows,'limits':['CFG follows direct branches only; calls and indirect targets are not followed.','Metadata adjacency identifies candidates but does not name a getter/setter unless independent evidence supports it.','Instruction dump capped at 64 linear instructions and CFG capped at 128 instructions/span 0x1000.']}
 dest=Path(__file__).parent/'02-char-callback-cfg.json';dest.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
 print(json.dumps({'sha256':pe.sha,'unique_targets':len(starts),'cfg_count':sum(x['cfg_instruction_count'] for x in rows),'output':str(dest)},indent=2))
if __name__=='__main__':main()

