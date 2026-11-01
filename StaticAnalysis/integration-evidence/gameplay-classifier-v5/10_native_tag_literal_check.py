from pathlib import Path
import hashlib,json
p=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
b=p.read_bytes();sha=hashlib.sha256(b).hexdigest();expected='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
if sha!=expected: raise SystemExit(f'pinned target mismatch: {sha}')
terms=[b'IsPlayerCombatAvatar',b'IsCombatAvatar',b'IsATMGuardAI']
found={}
for term in terms:
 offsets=[];at=0
 while True:
  at=b.find(term,at)
  if at<0:break
  offsets.append(at);at+=1
 found[term.decode()]=[hex(x) for x in offsets]
out={'path':str(p),'size':len(b),'sha256':sha,'ascii_literal_search':found,'scope':'static byte search only; absence of exact ASCII literals does not exclude encoded metadata or another registration route'}
Path(__file__).with_name('10_native_tag_literal_check.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print(json.dumps(out,indent=2))
