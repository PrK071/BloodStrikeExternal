# Python 3.12 | Native static-link probe for ClientPlayer.Char and IGameplay.Player.
"""Read-only PE/RTTI metadata inventory for the native ClientPlayer to Character link."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,references
PROPS=['Messiah.ClientPlayer.Char','IGameplay.Player']
TYPE_TERMS=['ClientPlayer','IPlayer','IGameplay','ActorComponent','SkeletonComponent','Character::Actor','Character::IActor','Character::ActorComponent','CharacterImp']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 old=ROOT/'results';hierp=old/'rtti-hierarchies.json';typesp=old/'rtti-types.json'
 hier=json.loads(hierp.read_text(encoding='utf-8'));types=json.loads(typesp.read_text(encoding='utf-8'))
 exact=[]
 for row in hier:
  if any(t.lower() in row.get('name','').lower() for t in TYPE_TERMS):
   exact.append({'rva':row['rva'],'type_descriptor_rva':row['type_descriptor_rva'],'name':row['name'],'object_offset':row['object_offset'],'bases':[b['name'] for b in row['bases']]})
 decorated=[]
 for row in types:
  name=row.get('decorated_name','')
  if any(t.lower() in name.lower() for t in TYPE_TERMS):decorated.append({'type_descriptor_rva':row['type_descriptor_rva'],'name_rva':row['name_rva'],'decorated_name':name})
 string_refs=[];targets={}
 for prop in PROPS:
  needle=prop.encode('ascii');start=0;found=0
  while True:
   at=pe.d.find(needle,start)
   if at<0:break
   end=at+len(needle)
   if end<len(pe.d) and pe.d[end]==0:
    r=pe.rva(at)
    if r is not None:
     found+=1;targets[r]=prop
     string_refs.append({'property':prop,'file_offset':hex(at),'rva':hex(r),'bytes':pe.d[at:end+1].hex(' ')})
   start=at+1
 refs=references(pe,targets)
 windows=[]
 for ref in refs:
  if ref['kind']!='data_pointer':continue
  slot=int(ref['rva'],16);off=pe.offset(slot)
  if off is None:continue
  lo=max(0,off-0x80);hi=min(len(pe.d),off+0x100)
  ptrs=[]
  for po in range((max(0,off-0x80)+7)//8*8,min(len(pe.d),off+0x100),8):
   val=struct.unpack_from('<Q',pe.d,po)[0];target=val-pe.base
   if pe.code(target) or pe.string(target):ptrs.append({'file_offset':hex(po),'rva':hex(pe.rva(po)),'value':hex(val),'target_rva':hex(target),'target_code':pe.code(target),'target_string':pe.string(target)})
  windows.append({'property':ref['target'],'pointer_slot_rva':ref['rva'],'file_offset':ref['file_offset'],'pointer_value_bytes':pe.d[off:off+8].hex(' '),'window_file_offset':hex(lo),'window_rva':hex(pe.rva(lo)),'pointers':ptrs})
 out={'binary':str(args.binary),'sha256':pe.sha,'pinned_sha256':PINNED,'rtti_hierarchies_sha256':hashlib.sha256(hierp.read_bytes()).hexdigest(),'rtti_hierarchies_rows':len(hier),'rtti_types_sha256':hashlib.sha256(typesp.read_bytes()).hexdigest(),'rtti_types_rows':len(types),'rtti_candidates':exact,'decorated_type_descriptors':decorated,'property_string_occurrences':string_refs,'data_pointer_windows':windows,'limits':['Exact names and reflected metadata do not establish runtime ownership.','Data and code are static; no process or target execution.']}
 dest=Path(__file__).parent/'01-link-probe.json';dest.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
 print(json.dumps({'sha256':pe.sha,'hier_rows':len(hier),'type_candidates':len(exact),'decorated_candidates':len(decorated),'property_occurrences':len(string_refs),'pointer_windows':len(windows),'output':str(dest)},indent=2))
if __name__=='__main__':main()
