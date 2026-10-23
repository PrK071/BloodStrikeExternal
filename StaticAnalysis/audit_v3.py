# Python | audit_v3.py | Python 3.12+, local iced-x86 and Capstone | AMD64 PE files only.
"""V3 evidence extraction. Reads the sample as data; never loads it as executable code."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import time

from audit_v2 import RawPE, PINNED, cfg, save
from iced_x86 import Decoder, OpKind, FlowControl
sys.path.insert(0, str(Path(__file__).parent/'vendor'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_MEM, X86_OP_IMM, X86_REG_RIP

TARGETS = {int(x,16) for x in '''8b7cd90 19d45e0 254390 ad0640 4f64210
580bcd8 952640 952660 8967f0 896f80 19c0100 29a9030 80cfff0'''.split()}
SEEDS = {int(x,16) for x in '''3259770 19b9360 1a52d0 254390 ad0640
19bf520 19bf730 19bfe20 19c0100 19bfb60 19d4b00 19d4eb0 1a1e560
ad6090 a030d0 1416d0 19d7b40 1a0d7e0 19c4610 19c5490 19c55e0
19c6690 19c6850 19c7e10 19d7300 19f3dc0 1a26c80 19d45e0
3203e50 3226040 3226aa0 32353b0 325a020 225740
2d829a0 2d82d90 2d84e90 2d82a00 2d82b80 2d845b0
10e8a0 10e1f0 10e3f0 10e410 10ea20 10ea90 10eaa0 2d85a60 29a9030 29abcd0 29aec10
29c1b40 2148220 20cc530 212ded0 ab720 141670 10e480
58b3e0 58b430 141d50 88ca20 952640 952660 952710 952740
8967f0 896f80 89f000 89f1b0 892b70 16d17d0 1163300 16d17e0 1163340'''.split()}
SNAPSHOTS = [
 ('V3-D01',0x4f64210,0x110,'IEntity.IsInWorld descriptor'),
 ('V3-D02',0x4ed0e40,0x110,'IComponent.Parent descriptor'),
 ('V3-D03',0x7998b00,0x50,'ActorComponent native registration'),
 ('V3-D04',0x580bcd0,0x38,'ActorComponent factory COL pointer and callable slots'),
 ('V3-D05',0x580b048,0x28,'PyActorComponent COL pointer and virtual slots'),
 ('V3-D06',0x559b8f0,0xf0,'ActorComponent COL pointer and primary virtual slots'),
 ('V3-D07',0x7a07d30,0x150,'Python type storage used by ActorComponent factory'),
 ('V3-D08',0x5565058,0x50,'Character Actor COL pointer and virtual slots'),
]

def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()

def baseline(root):
 manifest=json.loads((root/'audit-v2/artifact-sha256.json').read_text())
 checks=[]
 for name,expected in manifest.items():
  p=(root/'audit-v2'/name).resolve();actual=sha(p)
  checks.append(dict(path=str(p),expected=expected,actual=actual,match=actual==expected))
 if not all(c['match'] for c in checks):raise ValueError('V2 artifact manifest mismatch')
 paths=set((root/'audit-v2').glob('*'))|set((root/'results').glob('*.json'))
 paths|={root/n for n in ('AUDITORIA-V2.md','RELATORIO.md','audit_v2.py','curate_audit_v2.py','verify_evidence.py')}
 hashes={str(p.relative_to(root)):sha(p) for p in sorted(paths) if p.is_file()}
 return dict(manifest_checks=checks,input_sha256=hashes,
             inherited_claim_ids=[c['id'] for c in json.loads((root/'audit-v2/claims.json').read_text())])

def global_scan(pe):
 refs=[];count=0;invalid=[];started=time.perf_counter()
 for j,(b,e,u) in enumerate(pe.functions):
  o=pe.offset(b,e-b)
  if o is None:raise ValueError('Unbacked runtime record')
  for ins in Decoder(64,pe.d[o:o+e-b],ip=pe.base+b):
   count+=1
   if ins.is_invalid:invalid.append(hex(ins.ip-pe.base));continue
   target=None
   if ins.is_ip_rel_memory_operand:target=ins.ip_rel_memory_address-pe.base
   elif ins.flow_control in (FlowControl.CALL,FlowControl.UNCONDITIONAL_BRANCH,FlowControl.CONDITIONAL_BRANCH) and ins.op0_kind in (OpKind.NEAR_BRANCH16,OpKind.NEAR_BRANCH32,OpKind.NEAR_BRANCH64):target=ins.near_branch_target-pe.base
   if target in TARGETS:refs.append(dict(target_rva=hex(target),runtime_begin_rva=hex(b),instruction=pe.row(ins)))
  if j and j%100000==0:print('Scanned',j,'runtime records;',count,'decoded records',flush=True)
 return dict(decoded_records=count,runtime_records=len(pe.functions),invalid_instruction_rvas=invalid,
             references=refs,seconds=round(time.perf_counter()-started,3),
             scope='Linear decode within each unwind record; discovery only. Invalid instructions, embedded data and unlisted leaf code prevent a whole-program completeness claim.')

def masks(pe):
 functions={}
 for s in pe.sections:
  if not s['flags']&0x20000000:continue
  data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
  for m in re.finditer(re.escape(struct.pack('<I',0x130)),data):
   f=pe.function(s['rva']+m.start())
   if f:functions[f[0]]=f
 hits=[]
 for st in functions:
  for ins in pe.decode(st):
   if not ins.is_ip_rel_memory_operand and ins.memory_displacement==0x130 and ins.memory_base!=0:
    row=pe.row(ins);row['runtime_begin_rva']=hex(st);hits.append(row)
 return dict(candidate_runtime_records=len(functions),accesses=hits,
             scope='Displacement search, including unrelated objects and stack frames. A matching displacement is not type evidence; leaf accessors are separately covered by CFG seeds.')

def snapshot(pe,id,r,n,label):
 o=pe.offset(r,n)
 return dict(id=id,label=label,rva=hex(r),preferred_va=hex(pe.base+r),file_offset=hex(o),
             bytes=pe.d[o:o+n].hex(' '),qwords=[dict(rva=hex(r+i),value=hex(v),
             dir64_relocation=r+i in pe.relocations,target_rva=hex(v-pe.base) if pe.base<=v<pe.base+pe.size else None,
             target_string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None)
             for i in range(0,n,8) for v in [pe.unpack('<Q',r+i)[0]]])

def hierarchies(pe,root):
 old=json.loads((root/'results/rtti-hierarchies.json').read_text())
 names={'Character::Actor','AnimationCore::Skeleton','Messiah::ActorComponent','Messiah::SkeletonComponent',
        'Messiah::ISkeletonComponent','Messiah::IComponent','Messiah::IObject','Messiah::IEntity',
        'Messiah::PyActorComponent','Messiah::PySkeletonComponent','Messiah::PyISkeletonComponent',
        'Messiah::PyIComponent','Messiah::PyIObject'}
 chosen=[h for h in old if h['name'] in names or 'RegisterObjectClass__ActorComponent' in h['name']]
 result=[]
 for h in chosen:
  col=int(h['rva'],16);sig,offset,cd,td,ch,selfr=pe.unpack('<6I',col)
  assert sig==1 and selfr==col and offset==h['object_offset']
  hs,attr,n,arr=pe.unpack('<4I',ch);bases=[]
  assert n==len(h['bases'])
  for j in range(n):
   bd=pe.unpack('<I',arr+j*4)[0];btd,contained,md,pd,vd,attrs=pe.unpack('<IIiiiI',bd)
   assert btd==int(h['bases'][j]['type_descriptor_rva'],16) and md==h['bases'][j]['member_displacement']
   bases.append(dict(descriptor_rva=hex(bd),type_descriptor_rva=hex(btd),raw_name=pe.string(btd+16),
                     inherited_display_name=h['bases'][j]['name'],member_displacement=md,attributes=hex(attrs)))
  result.append(dict(col_rva=hex(col),name=h['name'],raw_name=pe.string(td+16),object_offset=offset,bases=bases))
 descendants=sorted({h['name'] for h in old if any(b['name']=='Messiah::ActorComponent' for b in h['bases'])})
 return dict(selected=result,actor_component_descendants_in_prior_inventory=descendants,
             limitation='Display names inherited; raw type descriptors and hierarchy relations re-read. Inventory absence cannot exclude RTTI-free or dynamically supplied classes.')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--binary',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'))
 p.add_argument('--out',type=Path,default=Path(__file__).parent/'audit-v3')
 a=p.parse_args();root=Path(__file__).parent;started=time.perf_counter();a.out.mkdir(parents=True,exist_ok=True)
 save(a.out/'summary.json',dict(status='RUNNING',note='No success published until verification completes'))
 try:
  pe=RawPE(a.binary)
  if pe.sha!=PINNED:raise ValueError('Sample SHA-256 differs from V2')
  locked=baseline(root);save(a.out/'baseline-lock.json',locked)
  scan=global_scan(pe);save(a.out/'global-scan.json',scan)
  candidates=masks(pe);save(a.out/'mask-candidates.json',candidates)
  seeds=SEEDS|{int(r['runtime_begin_rva'],16) for r in scan['references'] if r['target_rva']=='0x8b7cd90'}
  graphs=[cfg(pe,st,max_instructions=30000,span=0x100000) for st in sorted(seeds)]
  if any(g['capped'] for g in graphs):raise ValueError('CFG budget exceeded')
  unique={r['rva']:r for g in graphs for r in g['instructions']}
  decoder=Cs(CS_ARCH_X86,CS_MODE_64);decoder.detail=True;failures=[];rip_checks=0;branch_checks=0;indirect=[]
  for addr,row in unique.items():
   raw=bytes.fromhex(row['bytes']);cs=list(decoder.disasm(raw,int(row['preferred_va'],16),count=1))
   if len(cs)!=1 or cs[0].size!=row['length'] or bytes(cs[0].bytes)!=raw:
    failures.append(dict(rva=addr,kind='second_decoder_length_or_bytes'))
   elif 'rip_target_rva' in row:
    targets=[cs[0].address+cs[0].size+op.mem.disp-pe.base for op in cs[0].operands if op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP]
    if targets!=[int(row['rip_target_rva'],16)]:failures.append(dict(rva=addr,kind='second_decoder_rip_target'))
    rip_checks+=1
   if cs and 'branch_target_rva' in row:
    targets=[op.imm-pe.base for op in cs[0].operands if op.type==X86_OP_IMM]
    if targets!=[int(row['branch_target_rva'],16)]:failures.append(dict(rva=addr,kind='second_decoder_branch_target'))
    branch_checks+=1
   ins=Decoder(64,raw,ip=int(row['preferred_va'],16)).decode()
   if ins.flow_control in (FlowControl.INDIRECT_CALL,FlowControl.INDIRECT_BRANCH):
    indirect.append(dict(rva=addr,kind='call' if ins.flow_control==FlowControl.INDIRECT_CALL else 'jump',text=row['text']))
   if pe.d[int(row['file_offset'],16):int(row['file_offset'],16)+len(raw)]!=raw:raise ValueError('Byte mismatch')
  if failures:raise ValueError('Independent decoder disagreement: '+str(failures[:5]))
  for graph in graphs:
   for row in graph['instructions']:row['evidence_id']='V3-I-'+row['rva'][2:].upper()
  save(a.out/'reachable-code.json',graphs)
  save(a.out/'indirect-transfers.json',indirect)
  (a.out/'disassembly.txt').write_text('\n'.join(
   row['evidence_id']+' RVA '+row['rva']+' FO '+row['file_offset']+' '+row['bytes']+' '+row['text']
   for row in sorted(unique.values(),key=lambda r:int(r['rva'],16)))+'\n',encoding='utf8')
  save(a.out/'data-evidence.json',[snapshot(pe,*x) for x in SNAPSHOTS])
  for slot,expected in ((0x4f64210,'IEntity'),(0x4f64220,'bool'),(0x4f64230,'IsInWorld'),
                        (0x4f64240,'IEntity.IsInWorld'),(0x4ed0e40,'IComponent'),(0x4ed0e50,'IObject'),
                        (0x4ed0e70,'IComponent.Parent'),(0x7998b00,'ActorComponent')):
   assert pe.string(pe.unpack('<Q',slot)[0]-pe.base)==expected
  for slot,target in ((0x4f642d0,0x952640),(0x4f642d8,0x952660),(0x4f642f0,0x952710),
                      (0x4f642f8,0x952740),(0x4ed0f00,0x58b3e0),(0x580bce8,0x29abcd0)):
   assert slot in pe.relocations and pe.unpack('<Q',slot)[0]-pe.base==target
  save(a.out/'hierarchies.json',hierarchies(pe,root))
  claims=json.loads((root/'v3-claims-spec.json').read_text(encoding='utf8'))
  for c in claims:
   c['sample_sha256']=pe.sha;c['runtime_validation']=False
   c['instruction_evidence']=[unique[hex(int(x,16))]['evidence_id'] for x in c.pop('instruction_rvas')]
  save(a.out/'claims.json',claims)
  legacy=json.loads((root/'audit-v2/claims.json').read_text())
  save(a.out/'v2-claim-state.json',[dict(id=c['id'],v2_status=c['status'],v2_claim=c['claim'],
        v3_related=[x['id'] for x in claims if c['id'] in x['legacy_ids']]) for c in legacy])
  mapped=sorted({int(x['rva'],16) for x in unique.values()}|{x[1] for x in SNAPSHOTS})
  save(a.out/'address-map.json',[dict(rva=hex(r),preferred_va=hex(pe.base+r),file_offset=hex(pe.offset(r)),
        section=pe.section(r)['name']) for r in mapped])
  assert baseline(root)==locked,'Prior artifacts changed during extraction'
  assert sha(a.binary)==PINNED,'Sample changed during extraction'
  summary=dict(status='PASS_SELECTED_EVIDENCE',sha256=pe.sha,binary=str(a.binary),
       generated_utc=datetime.now(timezone.utc).isoformat(),image_base_preferred=hex(pe.base),
       runtime_records_scanned=scan['runtime_records'],decoded_discovery_records=scan['decoded_records'],
       invalid_discovery_records=len(scan['invalid_instruction_rvas']),global_reference_records=len(scan['references']),
       root_direct_references=sum(x['target_rva']=='0x8b7cd90' for x in scan['references']),
       getter_direct_references=sum(x['target_rva']=='0x19d45e0' for x in scan['references']),
       cfg_entries=len(graphs),unique_reachable_instructions=len(unique),second_decoder_mismatches=failures,
       independent_rip_target_checks=rip_checks,independent_branch_target_checks=branch_checks,
       indirect_transfers=len(indirect),
       cfg_entries_crossing_unwind=sum(len(g['runtime_records'])>1 for g in graphs),
       unclosed_cfg_targets={g['entry_rva']:g['unfollowed_targets'] for g in graphs if g['unfollowed_targets']},
       mask_candidate_accesses=len(candidates['accesses']),claims_by_status=dict(Counter(c['status'] for c in claims)),
       old_artifacts_unchanged=True,sample_hash_rechecked=True,runtime_game_access=False,
       seconds=round(time.perf_counter()-started,3),
       limitations='PASS applies only to selected byte/length/metadata evidence. Discovery decode is not a whole-image validity or reachability result. Direct calls are separate CFG seeds; unresolved indirect transfers and external tails remain explicit.')
  save(a.out/'summary.json',summary)
  print(json.dumps(summary,indent=2),flush=True)
 except Exception as exc:
  save(a.out/'summary.json',dict(status='FAIL',error=repr(exc),runtime_game_access=False))
  raise

if __name__=='__main__':main()
