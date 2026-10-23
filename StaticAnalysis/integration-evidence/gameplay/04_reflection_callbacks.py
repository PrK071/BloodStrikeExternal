# Python 3.12 | bounded disassembly for reflection-metadata callback candidates.
"""Decode candidate code pointers adjacent to selected reflected-property records."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED
ADDRS={'IGameplay.Player_candidate_a':0x58b020,'IGameplay.Player_candidate_b':0x940a20,'IGameplay.Player_candidate_c':0x92bec0,'IGameplay.Player_candidate_d':0x948bd0,'IGameplay.Player_candidate_e':0x948b90,'ClientPlayer.Char_candidate_a':0xcef390,'ClientPlayer.Char_candidate_b':0xcef3b0,'ClientPlayer.Char_candidate_c':0xcef410,'ClientPlayer.Char_candidate_d':0xcef430,'ClientPlayer.Char_candidate_e':0xcef450}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 out={'sha256':pe.sha,'code_pointer_candidates':[],'limitation':'Adjacency in a reflected-property metadata structure makes these callback candidates; names and exact getter/setter semantics are not established.'}
 for label,start in ADDRS.items():
  f=pe.function(start);ins=pe.decode(start,2048);rows=[pe.row(x) for x in ins[:48]]
  out['code_pointer_candidates'].append({'label':label,'entry_rva':hex(start),'runtime_function':[hex(v) for v in f] if f else None,'instructions':rows})
 p=Path(__file__).parent/'reflection-callbacks.json';p.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
 print(json.dumps({'sha256':pe.sha,'candidate_count':len(out['code_pointer_candidates']),'output':str(p)},indent=2))
if __name__=='__main__':main()
