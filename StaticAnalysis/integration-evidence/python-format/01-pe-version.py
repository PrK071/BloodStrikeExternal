import sys,re,json
from pathlib import Path
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
res=[]
for m in re.finditer(rb'[ -~]{5,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if (('Python' in s or 'python' in s) and any(t in s for t in ['3.','version','Version','dll','marshal'])) or re.match(r'^3\.(?:10|11|12|13|14)\.',s):res.append({'rva':hex(pe.rva(m.start())),'string':s[:500]})
Path(__file__).with_name('pe-version-strings.json').write_text(json.dumps(res,indent=2));print(json.dumps(res[:80],indent=2))
