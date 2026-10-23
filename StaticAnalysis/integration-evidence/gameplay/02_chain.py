# Python 3.12 | RawPE-only RTTI/reflection chain inspection.
"""Validate selected gameplay RTTI, reflected string refs, and vtable/code uses."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED,references
NAMES=['Messiah::IPlayer','Messiah::ClientPlayer','Messiah::ActorComponent','Messiah::SkeletonComponent','Messiah::ISkeletonComponent','Messiah::IComponent','Messiah::IObject','Messiah::IEntity','Messiah::IGameplay','Messiah::CharacterImpModule']
STRINGS=['IGameplay.Player','Messiah.ClientPlayer.Char','Messiah.ClientPlayer.KeyRepeatOV','CharacterImp.ActorComponent.IsEnableVisibilityOptimize']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 hier_path=ROOT/'results'/'rtti-hierarchies.json';types_path=ROOT/'results'/'rtti-types.json'
 hier=json.loads(hier_path.read_text(encoding='utf-8'));types=json.loads(types_path.read_text(encoding='utf-8'))
 selected=[];cols=[]
 for row in hier:
  if row.get('name') in NAMES:
   col=int(row['rva'],16);td=int(row['type_descriptor_rva'],16)
   sig,off,cd,td2,ch,selfr=pe.unpack('<6I',col)
   selected.append({'name':row['name'],'col_rva':row['rva'],'col_raw':pe.d[pe.offset(col,24):pe.offset(col,24)+24].hex(' '),'type_descriptor_rva':row['type_descriptor_rva'],'bases':[{'name':b['name'],'member_displacement':b.get('member_displacement'),'descriptor_rva':b.get('descriptor_rva'),'type_descriptor_rva':b.get('type_descriptor_rva')} for b in row['bases']],'rtti_self_check':{'signature':sig,'object_offset':off,'construction_displacement':cd,'type_descriptor_matches':td2==td,'hierarchy_rva':hex(ch),'self_rva_matches':selfr==col}})
   cols.append((row['name'],col,row['rva']))
 refs=[];vftables=[];targets={}
 for name,col,colhex in cols:targets[col]='COL '+name
 for row in selected:targets[int(row['type_descriptor_rva'],16)]='type descriptor '+row['name']
 for label in STRINGS:
  needle=label.encode('ascii');pos=0;found=0
  while True:
   at=pe.d.find(needle,pos)
   if at<0:break
   end=at+len(needle)
   if end<len(pe.d) and pe.d[end]==0:
    rva=pe.rva(at)
    if rva is not None:
     targets[rva]='string '+label;found+=1
     if found<=5:refs.append({'label':label,'file_offset':hex(at),'rva':hex(rva),'bytes_hex':pe.d[at:end+1].hex(' ')})
   pos=at+1
 # Locate RTTI vftables by data pointers to complete object locators; inspect referenced code and initial slots.
 for name,col,colhex in cols:
  ptr=struct.pack('<Q',pe.base+col);matches=[]
  for sec in pe.sections:
   if sec['flags']&0x20000000:continue
   lo=sec['raw_offset'];hi=lo+sec['raw_size'];pos=lo
   while True:
    at=pe.d.find(ptr,pos,hi)
    if at<0:break
    if (at-lo)%8==0 and at+16<=hi:
     vt_rva=pe.rva(at+8);slots=[]
     if vt_rva is not None:
      for i in range(12):
       slot=vt_rva+i*8;o=pe.offset(slot,8)
       if o is None:break
       t=struct.unpack_from('<Q',pe.d,o)[0]-pe.base
       if not pe.code(t):break
       slots.append({'slot_rva':hex(slot),'target_rva':hex(t)})
     if slots:matches.append({'col_pointer_file_offset':hex(at),'vtable_rva':hex(vt_rva),'slots':slots})
    pos=at+1
  vftables.append({'name':name,'col_rva':colhex,'candidate_vftables':matches[:16],'candidate_count':len(matches)})
 for v in vftables:
  for m in v['candidate_vftables']:
   r=int(m['vtable_rva'],16);targets[r]='vtable '+v['name']
 xrefs=references(pe,targets)
 # Keep only code refs and focused data refs for this output; source targets and bytes are emitted by RawPE.
 out={'binary':str(args.binary),'sha256':pe.sha,'pinned_sha256':PINNED,'rtti_hierarchies_sha256':hashlib.sha256(hier_path.read_bytes()).hexdigest(),'rtti_types_sha256':hashlib.sha256(types_path.read_bytes()).hexdigest(),'selected_hierarchies':selected,'reflected_string_occurrences_first20':refs,'rtti_vftable_candidates':vftables,'references':xrefs,'limits':['MSVC RTTI establishes type inheritance and vtable/COL linkage; it does not establish runtime instance identity or ownership.','String occurrences are candidate metadata until code/data references show use.','A candidate vtable reference is structural evidence; virtual slot semantics are not inferred from names alone.','The RTTI list is exhaustively searched for exact named types only; substring candidate counts are in catalog.json.']}
 path=Path(__file__).parent/'chain-evidence.json';path.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
 print(json.dumps({'sha256':pe.sha,'selected_hierarchy_rows':len(selected),'vtable_candidates':{x['name']:x['candidate_count'] for x in vftables},'reference_count':len(xrefs),'output':str(path)},indent=2))
if __name__=='__main__':main()

