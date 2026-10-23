# Python | prepare_focused_plan.py | Python 3.12 + iced-x86 | PE-bound Ghidra function selection, disk only.
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,cfg
parser=argparse.ArgumentParser();parser.add_argument('--function',action='append',help='RVA:analysis_label');parser.add_argument('--output',type=Path);args=parser.parse_args()
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha==PINNED
functions=[]
selected=[(int(x.split(':',1)[0],16),x.split(':',1)[1]) for x in args.function] if args.function else [(0x8977b0,'audited_entity_transform'),(0x19c0100,'audited_actor_association')]
for entry,label in selected:
 g=cfg(pe,entry,10000,0x100000);assert not g['capped'];ranges=[]
 for row in g['instructions']:
  start=int(row['preferred_va'],16);end=start+row['length']-1
  if ranges and ranges[-1][1]+1==start:ranges[-1][1]=end
  else:ranges.append([start,end])
 functions.append(dict(entry_va=hex(pe.base+entry),label=label,ranges=[[hex(b),hex(e)] for b,e in ranges],
  instructions=[dict(address=r['preferred_va'],bytes=r['bytes']) for r in g['instructions']],
  scope='Function body seeded from independently verified direct-branch CFG; callees not included.'))
out=args.output or Path(__file__).parent/'focused-plan.json';out.write_text(json.dumps(dict(sample_sha256=pe.sha,image_base=hex(pe.base),functions=functions),indent=2)+'\n')
print(json.dumps(dict(functions=len(functions),instruction_records=sum(len(x['instructions']) for x in functions))))
