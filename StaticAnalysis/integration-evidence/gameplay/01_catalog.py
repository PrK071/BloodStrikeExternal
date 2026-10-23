# Python 3.12 | static, disk-only RTTI and PE string catalogue.
"""Catalog gameplay-related RTTI hierarchy and raw PE string candidates; never load target."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE,PINNED
TERMS=['player','localplayer','playercontroller','charactercontroller','team','health','enemy','actorcomponent','parent','mcharacter','character','gameplay','skeleton','iobject','ientity','icomponent','iactor']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));ap.add_argument('--rtti',type=Path,default=ROOT/'results'/'rtti-hierarchies.json');args=ap.parse_args()
 pe=RawPE(args.binary)
 if pe.sha!=PINNED:raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')
 rows=json.loads(args.rtti.read_text(encoding='utf-8'))
 counts=collections.Counter();matches=[]
 for row in rows:
  own=row.get('name','');bases=[b.get('name','') for b in row.get('bases',[])]
  low=own.lower(); hits=[t for t in TERMS if t in low]
  if hits:
   counts.update(hits)
   matches.append({'rva':row['rva'],'type_descriptor_rva':row.get('type_descriptor_rva'),'name':own,'term_hits':hits,'bases':bases,'object_offset':row.get('object_offset'),'construction_displacement':row.get('construction_displacement')})
 ascii_hits=[];wide_hits=[];ascii_counts=collections.Counter();wide_counts=collections.Counter();raw=pe.d;lower=raw.lower()
 for term in TERMS:
  needle=term.encode('ascii');start=0
  while True:
   at=lower.find(needle,start)
   if at<0:break
   r=pe.rva(at)
   if r is not None:
    ascii_counts[term]+=1
    if ascii_counts[term]<=100:
     ascii_hits.append({'term':term,'file_offset':hex(at),'rva':hex(r),'context':raw[max(0,at-36):min(len(raw),at+len(needle)+48)].decode('ascii','replace')})
   start=at+1
  needle=term.encode('utf-16le');start=0
  while True:
   at=lower.find(needle,start)
   if at<0:break
   r=pe.rva(at)
   if r is not None:
    wide_counts[term]+=1
    if wide_counts[term]<=100:wide_hits.append({'term':term,'file_offset':hex(at),'rva':hex(r)})
   start=at+2
 out={'binary':str(args.binary),'sha256':pe.sha,'expected_sha256':PINNED,'rtti_file':str(args.rtti),'rtti_sha256':hashlib.sha256(args.rtti.read_bytes()).hexdigest(),'rtti_rows':len(rows),'term_counts_in_own_type_name':dict(counts),'candidate_hierarchies':matches,'raw_ascii_match_counts':dict(ascii_counts),'raw_utf16le_match_counts':dict(wide_counts),'raw_ascii_first_100_per_term':ascii_hits,'raw_utf16le_first_100_per_term':wide_hits,'limitations':['Substring matches are candidates only, not proof of gameplay classification.','RTTI hierarchies describe compiler type relationships, not runtime instances or parent/ownership semantics.','Raw PE text may be data or debug/editor content; only code-linked uses can strengthen interpretation.']}
 dest=Path(__file__).parent/'catalog.json';dest.write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
 print(json.dumps({'sha256':pe.sha,'rtti_rows':len(rows),'term_counts':dict(counts),'candidate_count':len(matches),'ascii_match_counts':dict(ascii_counts),'utf16_match_counts':dict(wide_counts),'output':str(dest)},indent=2))
if __name__=='__main__':main()


