from pathlib import Path
import sys,json,re,struct
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent
types=[];members=[]
for r in sorted(pe.relocations):
 try:
  v=pe.unpack('<Q',r)[0]-pe.base;name=pe.string(v)
 except ValueError:continue
 if name in ['function','code']:
  candidate=r-24
  try:
   q=pe.unpack('<8Q',candidate)
   if q[0]&0xffffffff!=0xc0000000 or q[2]!=0:continue
  except ValueError:continue
  types.append(dict(name=name,rva=hex(candidate),qwords=[hex(x) for x in pe.unpack('<50Q',candidate)],rows=[]))
 if name in ['__code__','__name__','__qualname__','__module__','co_names','co_consts','co_code','co_name','co_qualname']:
  members.append(dict(name=name,rva=hex(r),qwords=[hex(x) for x in pe.unpack('<5Q',r)],bytes=pe.d[pe.offset(r):pe.offset(r)+40].hex(' ')))
(O/'native-types-and-members.json').write_text(json.dumps(dict(types=types,members=members),indent=2))
print('types',[(x['name'],x['rva'],x['qwords'][4:6]) for x in types]);print('members',[(x['name'],x['rva'],x['qwords'][1:4]) for x in members])
