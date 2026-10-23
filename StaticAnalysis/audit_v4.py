# Python | audit_v4.py | Python 3.12 + iced-x86 + Capstone | pinned AMD64 PE, disk only.
"""Extract V4 evidence without loading the target or changing V2/V3 artifacts."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from audit_v2 import RawPE, PINNED, cfg, save
from iced_x86 import Decoder
sys.path.insert(0, str(Path(__file__).parent/'vendor'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_MEM, X86_OP_IMM, X86_REG_RIP

ROOT=Path(__file__).parent
SEEDS={
 'skeleton_constructor_a':0x115eb00,'skeleton_constructor_b':0x115e4c0,
 'character_constructor_a':0x16d0e70,'character_constructor_b':0x16d1190,
 'alternate_character_factory':0x1a1d760,'generic_skeleton_factory':0xad6760,
 'actor_component_factory':0x19bfe20,'actor_component_load':0x19c0000,
 'python_load_skeleton':0x29bb2f0,'association':0x19c0100,
 'insert':0x254390,'erase':0xad0640,'activation':0x19d4b00,
 'deactivation':0x19d4eb0,'actor_component_destructor':0x19bfb60,
 'deleting_destructor':0x1a1e560,'skeleton_component_destructor':0xad6090,
 'component_destructor':0x1416d0,'native_invalidation':0x10ea20,
 'association_cleanup':0x2d82b80,'wrapper_actor_expire':0x29a8e60,
 'wrapper_skeleton_expire':0x2148390,'wrapper_iskeleton_expire':0x20cc6b0,
 'wrapper_component_expire':0x212e050,'wrapper_iobject_expire':0x2d85f40,
 'deferred_cleanup':0x4fa950,'cleanup_threshold':0x4fa8c0,
 'cleanup_caller':0x52a530,'other_callback_call_a':0x10e3f0,
 'other_callback_call_b':0x10eaa0,'cleanup_callback_setter':0x10ea90,
 'python_context_init':0x2d845b0,'conversion':0x2d82d90,
 'pyobjects_constructor':0x1cb7100,'lazy_resolver_adapter':0x1cb85b0,
 'lazy_class_resolution':0x20cb120,'lazy_resolution_context':0x1cb72d0,
 'pending_vector_tail':0x899eb0,'other_global_getter':0x34c790,
 'registry_getter':0x19d45e0,'get_all_actors':0x3259770,
 'async_actor_load':0x19bfed0,'async_closure_capture':0x1a0e730,
 'association_callback_a':0x19d7b40,'association_callback_b':0x1a0d7e0,
 'thread_context_helper':0x3f3950,'entity_transform_wrapper':0x954ad0,
 'entity_transform_getter':0x95e880,'camera_view_wrapper':0x93f1a0,
 'camera_view_getter':0x964090,
 'allocator_release_thunk':0x424c1b0,'skeleton_disable_flag':0x1163300,
}
DATA={
 'V4-D01':(0x79602f0,4,'shared counter, initial disk value'),
 'V4-D02':(0x55ca5e8,0x38,'lazy resolver COL pointer and virtual slots'),
 'V4-D03':(0x55c8f40,0x20,'PyObjectsModule COL pointer and virtual slots'),
 'V4-D04':(0x4f60590,0x48,'IEntity.Transform metadata'),
 'V4-D05':(0x4f601c0,0x10,'Transform member function and this adjustment'),
 'V4-D06':(0x4f43b10,0x48,'ICamera.ViewMatrix metadata'),
 'V4-D07':(0x4f45130,0x10,'ViewMatrix member function and this adjustment'),
 'V4-D08':(0x6fb7ce0,0x18,'resolver callable COL'),
 'V4-D09':(0x6fb6b90,0x18,'module COL'),
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--sample',type=Path,required=True);a=p.parse_args()
 out=ROOT/'audit-v4';out.mkdir(exist_ok=True)
 manifest=json.loads((ROOT/'audit-v3/artifact-sha256.json').read_text())
 lock={n:sha(ROOT/n) for n in manifest}
 assert lock==manifest,'V3 manifest mismatch'
 pe=RawPE(a.sample);assert pe.sha==PINNED,'Sample mismatch'
 seeds=dict(SEEDS)
 discovery_path=out/'discovery.json'
 discovery=json.loads(discovery_path.read_text()) if discovery_path.exists() else None
 if discovery:
  assert discovery['sha256']==PINNED
  for ref in discovery['references']:
   if ref['target_rva'] in ('0x8b7cd90','0x19d45e0'):
    start=int(ref['runtime_rva'],16)
    if start not in seeds.values():seeds['root_consumer_'+hex(start)[2:]]=start
 graphs=[dict(label=label,**cfg(pe,start,30000,0x100000)) for label,start in seeds.items()]
 assert not any(g['capped'] for g in graphs),'CFG limit reached'
 rows={r['rva']:r for g in graphs for r in g['instructions']}
 cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 for r in rows.values():
  r['evidence_id']='V4-I-'+r['rva'][2:].upper()
  addr=int(r['rva'],16);raw=bytes.fromhex(r['bytes']);o=pe.offset(addr,len(raw))
  assert pe.d[o:o+len(raw)]==raw
  i=Decoder(64,raw,ip=pe.base+addr).decode();c=list(cs.disasm(raw,pe.base+addr,count=1))
  assert not i.is_invalid and len(c)==1 and c[0].size==i.len==r['length']
  if 'rip_target_rva' in r:
   t=int(r['rip_target_rva'],16)
   assert i.ip_rel_memory_address-pe.base==t
   assert [x.mem.disp+c[0].address+c[0].size-pe.base for x in c[0].operands if x.type==X86_OP_MEM and x.mem.base==X86_REG_RIP]==[t]
  if 'branch_target_rva' in r:
   t=int(r['branch_target_rva'],16);assert i.near_branch_target-pe.base==t
   assert [x.imm-pe.base for x in c[0].operands if x.type==X86_OP_IMM]==[t]
 # Instruction records in each graph receive the same stable identifier.
 for g in graphs:
  for r in g['instructions']:r['evidence_id']=rows[r['rva']]['evidence_id']
 blocks=[]
 for name,(r,n,meaning) in DATA.items():
  off=pe.offset(r,n);assert off is not None
  blocks.append(dict(evidence_id=name,rva=hex(r),file_offset=hex(off),bytes=pe.d[off:off+n].hex(' '),description=meaning))
 rtti=[]
 for col in (0x6fb7ce0,0x6fb6b90):
  signature,offset,cd,td,chd,self_rva=pe.unpack('<6I',col)
  assert signature==1 and self_rva==col
  raw_name=pe.string(td+16);assert raw_name and 'PyObjectsModule' in raw_name
  off=pe.offset(td);n=16+len(raw_name.encode('ascii'))+1
  rtti.append(dict(col_rva=hex(col),type_descriptor_rva=hex(td),raw_name=raw_name,
   descriptor_bytes=pe.d[off:off+n].hex(' '),descriptor_file_offset=hex(off),object_offset=offset))
 save(out/'resolver-rtti.json',rtti)
 assert pe.unpack('<I',0x79602f0)[0]==1
 for r,t in [(0x4f601c0,0x95e880),(0x4f45130,0x964090),(0x55ca600,0x1cb85b0)]:
  assert pe.unpack('<Q',r)[0]==pe.base+t,(hex(r),hex(t))
 assert pe.unpack('<i',0x4f601c8)[0]==pe.unpack('<i',0x4f45138)[0]==0
 claims=[
  ('V4-K01','Two Skeleton constructors fetch-add the same 32-bit counter and store the returned old value at +0x0c.','confirmed_static',['115eb42','115eb4a','115e502','115e50a']),
  ('V4-K02','Both Character::Actor construction paths call those Skeleton constructors.','confirmed_static',['16d0e9a','16d11b2']),
  ('V4-K03','Existing-key insertion returns without payload replacement.','confirmed_static',['254422','254435','254438']),
  ('V4-K04','A deferred cleanup path invalidates the wrapper before invoking the native virtual destructor.','confirmed_path',['4faa28','4faa35']),
  ('V4-K05','Wrapper expiration clears W+0x18; Python method checks reject an expired native object.','confirmed_path',['2d85fe7','29bb2f4','29bb2f8','29bb313']),
  ('V4-K06','Metadata resolver has a concrete adapter and name-based pending registration path.','confirmed_path',['1cb85b0','20cb175','20cb194','20cb1b9','20cb1d8']),
  ('V4-K07','Entity Transform and camera ViewMatrix getters return addresses, not a world-to-screen result.','confirmed_static',['95e880','964090']),
 ]
 result=[]
 for name,statement,status,ids in claims:
  evidence=[]
  for x in ids:
   row=rows.get(hex(int(x,16)));assert row is not None,(name,x)
   evidence.append(row['evidence_id'])
  result.append(dict(id=name,statement=statement,status=status,instructions=evidence))
 save(out/'reachable-code.json',graphs);save(out/'data-evidence.json',blocks);save(out/'claims.json',result)
 save(out/'instruction-index.json',rows)
 if discovery:
  coverage=[]
  for ref in discovery['references']:
   if ref['target_rva'] in ('0x8b7cd90','0x19d45e0'):
    rva=ref['instruction']['rva'];assert rva in rows
    coverage.append(dict(target_rva=ref['target_rva'],entry_rva=ref['runtime_rva'],instruction_id=rows[rva]['evidence_id'],status='reachable_cfg_and_bytes_verified; alias propagation not exhaustive'))
  save(out/'root-consumer-coverage.json',coverage)
 imports=[]
 desc=pe.dirs[1][0]
 while desc:
  oft,stamp,chain,name,ft=pe.unpack('<IIIII',desc)
  if not any((oft,stamp,chain,name,ft)):break
  dll=pe.string(name);j=0
  while True:
   value=pe.unpack('<Q',(oft or ft)+j*8)[0]
   if not value:break
   symbol=('ordinal:'+str(value&0xffff)) if value>>63 else pe.string(value+2)
   if ft+j*8==0x4e34860:imports.append(dict(iat_rva=hex(ft+j*8),dll=dll,symbol=symbol))
   j+=1
  desc+=20
 save(out/'selected-imports.json',imports)
 assert {n:sha(ROOT/n) for n in manifest}==lock,'V3 changed during extraction'
 save(out/'input-lock.json',dict(sample_sha256=pe.sha,v3_manifest_sha256=sha(ROOT/'audit-v3/artifact-sha256.json'),v3_inputs=lock))
 summary=dict(status='PASS_SELECTED_V4_EVIDENCE',generated_utc=datetime.now(timezone.utc).isoformat(),sample_sha256=pe.sha,
  cfg_entries=len(graphs),unique_instructions=len(rows),instruction_records=sum(len(g['instructions']) for g in graphs),
  cross_unwind_entries=sum(len(g['runtime_records'])>1 for g in graphs),data_blocks=len(blocks),claims=len(result),
  byte_length_target_mismatches=0,unfollowed_targets={g['label']:g['unfollowed_targets'] for g in graphs if g['unfollowed_targets']},
  runtime_observations=0,game_process_access=False,v3_inputs_unchanged=True,
  limits='Selected reachable CFGs; calls require explicit seeds; no exhaustive computed-pointer, type, concurrency or runtime proof.')
 save(out/'summary.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
