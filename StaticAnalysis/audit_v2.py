# Python | audit_v2.py | Python 3.12+, iced-x86 1.21.0 | Windows x64, static files only.
"""Independent raw-PE parser and second decoder audit; never loads a target executable."""
import argparse
from bisect import bisect_right
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import struct
import sys
import time

sys.path.insert(0,str(Path(__file__).parent/'audit-vendor'))
from iced_x86 import Decoder,Formatter,FormatterSyntax,Mnemonic,OpKind,FlowControl

PINNED='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
FORMAT=Formatter(FormatterSyntax.INTEL)


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf8')


class RawPE:
    def __init__(self,path):
        self.path=path;self.d=path.read_bytes();self.sha=hashlib.sha256(self.d).hexdigest()
        if self.d[:2]!=b'MZ':raise ValueError('Missing MZ')
        p=struct.unpack_from('<I',self.d,0x3c)[0]
        if self.d[p:p+4]!=b'PE\0\0':raise ValueError('Missing PE')
        machine,n,self.timestamp,_,_,osize,_=struct.unpack_from('<HHIIIHH',self.d,p+4)
        o=p+24
        if machine!=0x8664 or struct.unpack_from('<H',self.d,o)[0]!=0x20b:raise ValueError('Not AMD64 PE32+')
        self.base=struct.unpack_from('<Q',self.d,o+24)[0]
        self.size,self.headers=struct.unpack_from('<II',self.d,o+56)
        self.entry=struct.unpack_from('<I',self.d,o+16)[0]
        self.dirs=[struct.unpack_from('<II',self.d,o+112+i*8) for i in range(16)]
        self.sections=[]
        for i in range(n):
            s=o+osize+i*40;name,vs,rva,rs,off=struct.unpack_from('<8sIIII',self.d,s)
            flags=struct.unpack_from('<I',self.d,s+36)[0]
            if rs and off+rs>len(self.d):raise ValueError('Section exceeds file')
            self.sections.append(dict(name=name.rstrip(b'\0').decode(),rva=rva,virtual_size=vs,raw_size=rs,
                                      raw_offset=off,flags=flags))
        self.functions=[]
        rva,size=self.dirs[3];off=self.offset(rva,size)
        if off is None or size%12:raise ValueError('Invalid exception directory')
        for begin,end,unwind in struct.iter_unpack('<III',self.d[off:off+size]):
            if not (begin<end<=self.size and self.code(begin) and self.offset(unwind) is not None):
                raise ValueError('Invalid RUNTIME_FUNCTION')
            self.functions.append((begin,end,unwind))
        if self.functions!=sorted(self.functions):raise ValueError('Unsorted exception records')
        self.starts=[x[0] for x in self.functions]
        self.relocations=set()
        rva,size=self.dirs[5];off=self.offset(rva,size);p=off
        if off is not None:
            while p<off+size:
                page,block=struct.unpack_from('<II',self.d,p)
                if block<8 or p+block>off+size or block%2:raise ValueError('Invalid relocation block')
                for item, in struct.iter_unpack('<H',self.d[p+8:p+block]):
                    if item>>12==10:self.relocations.add(page+(item&0xfff))
                p+=block

    def section(self,r):
        return next((s for s in self.sections if s['rva']<=r<s['rva']+max(s['raw_size'],s['virtual_size'])),None)

    def offset(self,r,n=1):
        if 0<=r and r+n<=min(self.headers,len(self.d)):return r
        s=self.section(r)
        if s and 0<=r-s['rva'] and r-s['rva']+n<=s['raw_size']:
            return s['raw_offset']+r-s['rva']
        return None

    def rva(self,o):
        s=next((s for s in self.sections if s['raw_offset']<=o<s['raw_offset']+s['raw_size']),None)
        return s['rva']+o-s['raw_offset'] if s else (o if 0<=o<self.headers else None)

    def code(self,r):
        s=self.section(r)
        return bool(s and s['flags']&0x20000000 and self.offset(r) is not None)

    def unpack(self,fmt,r):
        o=self.offset(r,struct.calcsize(fmt))
        if o is None:raise ValueError(f'Not file backed: {r:x}')
        return struct.unpack_from(fmt,self.d,o)

    def string(self,r,limit=2048):
        o=self.offset(r)
        if o is None:return None
        e=self.d.find(b'\0',o,min(o+limit,len(self.d)))
        if e<0:return None
        b=self.d[o:e]
        return b.decode('ascii') if all(32<=c<127 for c in b) else None

    def function(self,r):
        i=bisect_right(self.starts,r)-1
        return self.functions[i] if i>=0 and r<self.functions[i][1] else None

    def decode(self,start,max_size=131072):
        f=self.function(start);n=min(f[1]-start,max_size) if f else min(512,max_size)
        o=self.offset(start,n)
        if o is None:return []
        result=[]
        for ins in Decoder(64,self.d[o:o+n],ip=self.base+start):
            if ins.is_invalid:break
            result.append(ins)
            if not f and ins.flow_control in (FlowControl.RETURN,FlowControl.UNCONDITIONAL_BRANCH):break
        return result

    def row(self,ins):
        r=ins.ip-self.base;o=self.offset(r,ins.len)
        row=dict(rva=hex(r),preferred_va=hex(ins.ip),file_offset=hex(o),bytes=self.d[o:o+ins.len].hex(' '),
                 text=FORMAT.format(ins),length=ins.len)
        if ins.is_ip_rel_memory_operand:
            t=ins.ip_rel_memory_address-self.base
            row.update(rip_target_rva=hex(t),rip_target_string=self.string(t))
        if ins.flow_control in (FlowControl.CALL,FlowControl.UNCONDITIONAL_BRANCH,FlowControl.CONDITIONAL_BRANCH) and ins.op0_kind in (OpKind.NEAR_BRANCH16,OpKind.NEAR_BRANCH32,OpKind.NEAR_BRANCH64):
            row['branch_target_rva']=hex(ins.near_branch_target-self.base)
        return row


def legacy_audit(pe,old):
    def load(n):return json.loads((old/n).read_text(encoding='utf8'))
    mismatches=[];unique=set();total=0;units={}
    for fn in load('function-evidence.json'):
        start=int(fn['start_rva'],16);rows=fn['instructions']
        if not rows:continue
        end=int(rows[-1]['rva'],16)+len(bytes.fromhex(rows[-1]['bytes']))
        off=pe.offset(start,end-start)
        if off is None:raise ValueError('Legacy function not file backed')
        decoded={i.ip-pe.base:i for i in Decoder(64,pe.d[off:off+end-start],ip=pe.base+start)}
        units[start]=decoded
        for row in rows:
            r=int(row['rva'],16);expected=bytes.fromhex(row['bytes']);i=decoded.get(r);o=pe.offset(r,len(expected));total+=1
            if o is None or o!=int(row['file_offset'],16) or pe.d[o:o+len(expected)]!=expected or i is None or i.is_invalid or i.len!=len(expected):
                mismatches.append(dict(kind='instruction',rva=hex(r)))
            else:unique.add((r,i.len))
    refs=load('code-xrefs.json');cache={};xref_failures=[]
    for ref in refs:
        start=int(ref['function_begin_rva'],16);r=int(ref['instruction_rva'],16)
        if start not in cache:cache[start]={i.ip-pe.base:i for i in pe.decode(start,262144)}
        i=cache[start].get(r)
        if i is None or not i.is_ip_rel_memory_operand or i.ip_rel_memory_address-pe.base!=int(ref['target_rva'],16):
            xref_failures.append(ref)
    tables=[];slot_count=0
    for table in load('core-vtables.json'):
        r=int(table['vtable_rva'],16);col=int(table['col_rva'],16)
        colptr=pe.unpack('<Q',r-8)[0]-pe.base
        slots=[]
        for slot in table['entries']:
            a=int(slot['slot_rva'],16);t=int(slot['function_rva'],16);slot_count+=1
            slots.append(dict(slot_rva=hex(a),matches=pe.unpack('<Q',a)[0]==pe.base+t,
                              dir64_relocation=a in pe.relocations,code_target=pe.code(t)))
        tables.append(dict(name=table['name'],vtable_rva=hex(r),col_rva=hex(col),col_pointer_matches=colptr==col,
                           col_pointer_relocated=r-8 in pe.relocations,slots=slots))
    td_fail=[]
    tds=load('rtti-types.json')
    for td in tds:
        r=int(td['type_descriptor_rva'],16);v,spare=pe.unpack('<QQ',r)
        if spare or pe.string(r+16)!=td['decorated_name'] or v-pe.base!=int(td['type_info_vftable_rva'],16):td_fail.append(hex(r))
    return dict(instruction_records=total,unique_instruction_ranges=len(unique),decoder_mismatches=mismatches,
                xrefs_checked=len(refs),xref_failures=xref_failures,vtable_slots_checked=slot_count,
                tables=tables,type_descriptors_checked=len(tds),type_descriptor_failures=td_fail,
                note='Structural validation does not prove method semantics or exact vtable extents')


def hierarchy_audit(pe,old):
    result=[]
    for c in json.loads((old/'core-hierarchies.json').read_text()):
        col=int(c['rva'],16);sig,off,cd,td,h,selfr=pe.unpack('<6I',col)
        hs,attrs,n,arr=pe.unpack('<4I',h);bases=[];stack=[];edges=[]
        for index in range(n):
            bcd=pe.unpack('<I',arr+index*4)[0]
            btd,contained,md,pd,vd,ba,bchd=pe.unpack('<IIiiiII',bcd)
            name=pe.string(btd+16)
            while stack and index>stack[-1][1]:stack.pop()
            if stack:edges.append(dict(parent=stack[-1][0],child=name,member_displacement=md))
            stack.append((name,index+contained))
            bases.append(dict(index=index,descriptor_rva=hex(bcd),type_descriptor_rva=hex(btd),name=name,
                              contained_bases=contained,member_displacement=md,vbtable_displacement=pd,
                              displacement_inside_vbtable=vd,attributes=hex(ba),class_descriptor_rva=hex(bchd)))
        ok=(sig==1 and selfr==col and off==c['object_offset'] and cd==c['construction_displacement'] and
            td==int(c['type_descriptor_rva'],16) and hs==0 and attrs==int(c['hierarchy_attributes'],16) and n==len(c['bases']))
        for a,b in zip(bases,c['bases']):
            ok=ok and all(a[k]==b[k] for k in ('descriptor_rva','type_descriptor_rva','contained_bases','member_displacement','vbtable_displacement','displacement_inside_vbtable','attributes'))
        result.append(dict(name=c['name'],col_rva=hex(col),object_offset=off,class_hierarchy_rva=hex(h),
                           legacy_matches=ok,bases=bases,direct_edges=edges))
    return result


def references(pe,targets):
    found=[];cache={};seen=set()
    def accept(r,kind,target):
        f=pe.function(r)
        if not f or f[1]-f[0]>262144:return
        if f[0] not in cache:cache[f[0]]={i.ip-pe.base:i for i in pe.decode(f[0],262144)}
        ins=cache[f[0]].get(r)
        if not ins:return
        actual=(ins.ip_rel_memory_address-pe.base if kind=='rip' and ins.is_ip_rel_memory_operand else
                ins.near_branch_target-pe.base if kind=='branch' and ins.op0_kind in (OpKind.NEAR_BRANCH16,OpKind.NEAR_BRANCH32,OpKind.NEAR_BRANCH64) else None)
        if actual!=target or (r,kind) in seen:return
        seen.add((r,kind));found.append(dict(kind=kind,target=targets[target],target_rva=hex(target),
                                           function_begin_rva=hex(f[0]),function_end_rva=hex(f[1]),instruction=pe.row(ins)))
    rip=re.compile(rb'(?=([\x40-\x4f]?[\x8d\x8b\x89\x63][\x05\x0d\x15\x1d\x25\x2d\x35\x3d][\x00-\xff]{4}))')
    branch=re.compile(rb'(?=([\xe8\xe9][\x00-\xff]{4}))')
    for s in pe.sections:
        if not s['flags']&0x20000000:continue
        d=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
        for pattern,kind in ((rip,'rip'),(branch,'branch')):
            for m in pattern.finditer(d):
                raw=m.group(1);r=s['rva']+m.start();t=r+len(raw)+struct.unpack_from('<i',raw,len(raw)-4)[0]
                if t in targets:accept(r,kind,t)
    for target,label in targets.items():
        needle=struct.pack('<Q',pe.base+target)
        for s in pe.sections:
            if s['flags']&0x20000000:continue
            o,e=s['raw_offset'],s['raw_offset']+s['raw_size']
            while True:
                o=pe.d.find(needle,o,e)
                if o<0:break
                r=pe.rva(o)
                if r%8==0:found.append(dict(kind='data_pointer',target=label,target_rva=hex(target),rva=hex(r),
                                           file_offset=hex(o),dir64_relocation=r in pe.relocations))
                o+=1
    return found


def cfg(pe,start,max_instructions=10000,span=0x10000):
    """Reachable instruction graph; do not mistake unwind record boundaries for function exits."""
    pending=[start];visited={};edges=[];outside=[]
    while pending and len(visited)<max_instructions:
        r=pending.pop()
        if r in visited:continue
        if abs(r-start)>span or not pe.code(r):
            outside.append(hex(r));continue
        off=pe.offset(r);ins=Decoder(64,pe.d[off:off+15],ip=pe.base+r).decode()
        if ins.is_invalid:
            outside.append(hex(r));continue
        row=pe.row(ins);visited[r]=row
        if ins.flow_control==FlowControl.RETURN or ins.mnemonic==Mnemonic.INT3:continue
        if ins.flow_control==FlowControl.INDIRECT_BRANCH:continue
        if ins.flow_control in (FlowControl.CONDITIONAL_BRANCH,FlowControl.UNCONDITIONAL_BRANCH):
            target=ins.near_branch_target-pe.base
            edges.append(dict(source=hex(r),target=hex(target),kind='conditional' if ins.flow_control==FlowControl.CONDITIONAL_BRANCH else 'jump'))
            pending.append(target)
            if ins.flow_control==FlowControl.UNCONDITIONAL_BRANCH:continue
        pending.append(r+ins.len)
    records={}
    for r in visited:
        f=pe.function(r)
        if f:records[f[0]]=dict(begin=hex(f[0]),end=hex(f[1]),unwind=hex(f[2]))
    return dict(entry_rva=hex(start),instructions=[visited[r] for r in sorted(visited)],branch_edges=edges,
                runtime_records=list(records.values()),unfollowed_targets=sorted(set(outside)),
                capped=bool(pending),scope='direct branch reachability; calls not followed, tailcall identity unproven')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();start=time.perf_counter();a.out.mkdir(parents=True,exist_ok=True);pe=RawPE(a.binary)
    if pe.sha!=PINNED:raise ValueError('Different build; pinned audit aborted')
    audit=legacy_audit(pe,a.old);save(a.out/'legacy-audit.json',audit)
    hier=hierarchy_audit(pe,a.old);save(a.out/'hierarchies.json',hier)
    print('Legacy audit',audit['instruction_records'],'instruction records;',len(audit['decoder_mismatches']),'decoder mismatches',flush=True)
    targets={0x3259770:'GetAllActors callback',0x32362d0:'MCharacter module initializer candidate',
             0x19d45e0:'enumeration root getter',0x8b7cd90:'enumeration root pointer storage',
             0x8e455b8:'conversion context pointer storage',0x5bb8878:'GetAllActors string',
             0x5565060:'Character::Actor primary vftable',0x559b8f8:'ActorComponent primary vftable',
             0x559b9f0:'ActorComponent secondary vftable',0x4fa22a0:'SkeletonComponent primary vftable',
             0x4fa2390:'SkeletonComponent secondary vftable',0x4e57558:'ICamera primary vftable',
             0x8a8e810:'external unvalidated address'}
    refs=references(pe,targets);save(a.out/'references.json',refs)
    starts={0x3259770,0x32362d0,0x19d45e0,0x2a83270,0x2a83570,0x2d829a0,0x2d82d90,0x2a70dc0,
            0x1bff870,0x2abf8e0,0x2abfd80,0x2a94d90,0x2a9cba0,
            0x16d0e70,0x19bf520,0x19bf730,0xad5c10,0xad5d90,0x275720,
            0x115eb00,0xa03050,0x88ca20,0x1a1e2fc,0xb1070c,0x19bfe20,0x19c0100,0x1a52d0,0x254390}
    # The shared conversion context has >1000 references; retain every xref but dump only selected bodies.
    starts.update(int(r['function_begin_rva'],16) for r in refs if 'function_begin_rva' in r and
                  (r['target_rva']!='0x8e455b8' or r['instruction']['text'].startswith(('mov [','lea '))))
    functions=[];asm=[]
    for st in sorted(starts):
        f=pe.function(st);ins=pe.decode(st,262144);rows=[pe.row(x) for x in ins]
        functions.append(dict(start_rva=hex(st),runtime_function=[hex(x) for x in f] if f else None,
                              instructions=rows,truncated=bool(f and (not ins or ins[-1].next_ip-pe.base!=f[1]))))
        asm.append('\n; RVA '+hex(st))
        asm.extend(f"{x['rva']:>12} FO {x['file_offset']:>12} {x['bytes']:<46} {x['text']}" for x in rows)
    save(a.out/'functions.json',functions);(a.out/'disassembly.txt').write_text('\n'.join(asm)+'\n',encoding='utf8')
    cfg_seeds={0x3259770:'GetAllActors',0x2a83270:'list allocation helper',0x2a83570:'list append helper',
               0x2d82d90:'native to script association',0x2d829a0:'script wrapper result',
               0x2abf8e0:'native Python callable creation',0x2abfd80:'NOARGS dispatcher',
               0x19b9360:'enumeration registry allocation',0x1a52d0:'enumeration registry initialization',
               0x2d845b0:'generic conversion context allocation'}
    graphs=[]
    for st,label in cfg_seeds.items():
        graph=cfg(pe,st);graph['label']=label;graphs.append(graph)
    save(a.out/'reachable-code.json',graphs)
    module_def=0x7a94790;module_name_va=pe.unpack('<Q',module_def+0x28)[0]
    list_type=0x7a193e0;list_name_va=pe.unpack('<Q',list_type+0x18)[0]
    bridge=dict(module_definition_rva=hex(module_def),module_name_pointer_slot_rva=hex(module_def+0x28),
                module_name_rva=hex(module_name_va-pe.base),module_name=pe.string(module_name_va-pe.base),
                list_type_rva=hex(list_type),list_type_name_slot_rva=hex(list_type+0x18),
                list_type_name_rva=hex(list_name_va-pe.base),list_type_name=pe.string(list_name_va-pe.base),
                schema_limit='PyModuleDef and PyTypeObject interpretation corroborated by code/source patterns; fork layout not globally assumed')
    save(a.out/'script-bridge.json',bridge)
    addresses=sorted(set(targets)|starts|{int(c['vtable_rva'],16) for c in json.loads((a.old/'core-vtables.json').read_text())})
    mapping=[]
    for r in addresses:
        s=pe.section(r);o=pe.offset(r)
        mapping.append(dict(rva=hex(r),preferred_va=hex(pe.base+r),file_offset=hex(o) if o is not None else None,
                            section=s['name'] if s else None,file_backed=o is not None))
    save(a.out/'address-map.json',mapping)
    inputs={str(x.name):hashlib.sha256(x.read_bytes()).hexdigest() for x in a.old.glob('*.json')}
    for name in ('RELATORIO.md','analyze_static.py','verify_evidence.py'):
        inputs['../'+name]=hashlib.sha256((a.old.parent/name).read_bytes()).hexdigest()
    failed=(bool(audit['decoder_mismatches']) or bool(audit['xref_failures']) or bool(audit['type_descriptor_failures']) or
            any(not h['legacy_matches'] for h in hier) or
            any(not t['col_pointer_matches'] or any(not x['matches'] or not x['code_target'] for x in t['slots']) for t in audit['tables']))
    result=dict(generated_utc=datetime.now(timezone.utc).isoformat(),binary=str(a.binary),sha256=pe.sha,
                pe_timestamp_raw=hex(pe.timestamp),pe_timestamp_utc=datetime.fromtimestamp(pe.timestamp,timezone.utc).isoformat(),
                image_base_preferred=hex(pe.base),size_of_image=hex(pe.size),entry_point_rva=hex(pe.entry),
                decoder='iced-x86 '+importlib.metadata.version('iced-x86'),parser='independent raw struct PE parser in audit_v2.py',
                source_artifact_hashes=inputs,sections=pe.sections,runtime_function_entries=len(pe.functions),
                reference_records=len(refs),dumped_units=len(functions),status='FAIL' if failed else 'PASS_STRUCTURAL',
                wall_seconds=round(time.perf_counter()-start,3),runtime_game_access=False)
    if hashlib.sha256(a.binary.read_bytes()).hexdigest()!=pe.sha:raise ValueError('Binary changed during audit')
    save(a.out/'summary.json',result);print(json.dumps(result|{'source_artifact_hashes':'see summary.json','sections':'see summary.json'}),flush=True)
    if failed:raise SystemExit(2)


if __name__=='__main__':main()
