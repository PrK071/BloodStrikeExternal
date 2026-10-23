from pathlib import Path
import sys,json,struct,hashlib
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal');sys.path.insert(0,str(ROOT/'StaticAnalysis'));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
out=Path(__file__).parent;functions={}
for r in [0x8977b0,0x2d85310]:
 rows=[pe.row(i) for i in pe.decode(r)];functions[hex(r)]=rows
 print('\nFN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows))
f=pe.function(0x2d84498);rr=[pe.row(i) for i in pe.decode(f[0])];reg=[x for x in rr if 0x2d84470<=int(x['rva'],16)<0x2d84500];functions['registration']=reg
(out/'verified-instructions.json').write_text(json.dumps({'sample_sha256':pe.sha,'functions':functions},indent=2));print('REG',reg)
