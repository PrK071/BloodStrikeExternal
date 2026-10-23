# Python 3.12 | Static xrefs from ClientPlayer reflection metadata and RTTI closures.
"""Find native code references to ClientPlayer.Char registration metadata and closure RTTI."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,references,cfg

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 tpath=ROOT/'results'/'rtti-types.json';types=json.loads(tpath.read_text(encoding='utf-8'))
 names=['RegisterObjectClass__ClientPlayer','InitializeObjectClass__ClientPlayer','ClientPlayer@Messiah']
 targets={};selected=[]
 for row in types:
  n=row['decorated_name']
  if any(q in n for q in names) and ('lambda_1>@?4??RegisterObjectClass__ClientPlayer' in n or 'lambda_1>@?4??InitializeObjectClass__ClientPlayer' in n):
   r=int(row['type_descriptor_rva'],16);targets[r]='RTTI closure '+n[:180];selected.append({'rva':hex(r),'name':n})
 # Bind the exact metadata region, descriptor strings and likely offset accessors.
 for r,label in [(0x51c47e0,'string ClientPlayer.Char'),(0x51f9170,'ClientPlayer metadata block A'),(0x51f91e0,'ClientPlayer metadata block B'),(0x51f91f0,'ClientPlayer.Char reflected name slot'),(0x51f9210,'ClientPlayer.Char reflected duplicate slot'),(0x51f9230,'ClientPlayer.Char callback block'),(0x51f9280,'ClientPlayer.Char tail callback block'),(0xce4570,'ClientPlayer.Char offset-accessor candidate +0xea0'),(0x6a5850,'ClientPlayer.Char offset-accessor candidate +0xec0')]:targets[r]=label
 found=references(pe,targets)
 starts=sorted({int(x['function_begin_rva'],16) for x in found if x['kind'] in ('rip','branch') and 'function_begin_rva' in x})
 graphs=[]
 for start in starts:
  g=cfg(pe,start,max_instructions=400,span=0x4000);g['label']='xref caller of ClientPlayer reflection/RTTI target';graphs.append(g)
 out={'sha256':pe.sha,'rtti_types_sha256':hashlib.sha256(tpath.read_bytes()).hexdigest(),'selected_closure_descriptors':selected,'target_map':{hex(k):v for k,v in targets.items()},'references':found,'caller_functions':graphs,'limits':['Only statically decoded direct RIP and relative-branch references are captured; indirect and computed references may be missed.','Closure type descriptors identify lambdas but not source-level call semantics.','CFG follows direct branches only and does not follow callees or indirect branches.']}
 p=Path(__file__).parent/'03_registration-xrefs.json';p.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
 print(json.dumps({'sha256':pe.sha,'closure_descriptors':len(selected),'references':len(found),'caller_functions':len(graphs),'cfg_insns':sum(len(x['instructions']) for x in graphs),'output':str(p)},indent=2))
if __name__=='__main__':main()
