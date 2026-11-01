from pathlib import Path
import sys,json
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent;out={}
for r in [0x20566e0,0x102e10,0x2a1cb10,0x2d85a60]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:180]))
(O/'entity-allocation.json').write_text(json.dumps(out,indent=2))

