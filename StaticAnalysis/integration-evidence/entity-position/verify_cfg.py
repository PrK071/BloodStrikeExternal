from pathlib import Path
import json,sys,hashlib
OUT=Path(__file__).parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
source=json.loads((OUT/'verified-instructions.json').read_text());result={}
for name,rows in source['functions'].items():
 if name=='registration':continue
 by={int(x['rva'],16):x for x in rows};edges={};calls=[]
 for r,row in by.items():
  t=row['text'].split()[0];n=r+row['length'];target=int(row['branch_target_rva'],16) if 'branch_target_rva' in row else None
  if t=='call':calls.append({'rva':hex(r),'target':hex(target) if target else 'indirect'});succ=[n]
  elif t=='jmp':succ=[target] if target is not None else []
  elif t.startswith('j'):succ=[n,target] if target is not None else [n]
  elif t.startswith('ret'):succ=[]
  else:succ=[n]
  edges[r]=[x for x in succ if x in by]
 reachable=set();todo=[int(name,16)]
 while todo:
  r=todo.pop()
  if r in reachable:continue
  reachable.add(r);todo.extend(edges.get(r,[]))
 result[name]={'entry':name,'reachable_count':len(reachable),'decoded_count':len(rows),'all_decoded_reachable':len(reachable)==len(rows),'edges':{hex(k):[hex(x) for x in v] for k,v in edges.items()},'calls':calls}
# RTTI TypeDescriptor names passed into the dynamic cast.
types=[]
for r in [0x7dd90c8,0x7de5d78]:
 o=pe.offset(r,64);types.append({'rva':hex(r),'file_offset':hex(o),'bytes':pe.d[o:o+64].hex(' '),'name':pe.string(r+16)})
result['cast_types']=types
result['name']={'rva':'0x5b84910','text':pe.string(0x5b84910)}
(OUT/'cfg-and-types.json').write_text(json.dumps(result,indent=2));print([(k,v['all_decoded_reachable']) for k,v in result.items() if isinstance(v,dict) and 'all_decoded_reachable' in v]);print(types)

