from pathlib import Path
import sys,json,re
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
res=[]
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if any(t in s for t in ['AimPlacer','LerpBlender','BlendInPlacer','CameraController']):res.append({'rva':hex(pe.rva(m.start())),'string':s})
Path(__file__).with_name('native-name-inventory.json').write_text(json.dumps(res,indent=2));print(json.dumps(res[:60],indent=2))
