# Python | python-values-v6/01_values_proof.py | Python 3.12+ | pinned PE type identities and scalar layout proof.
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from ExternalCore.build import verify_sample


def main():
    sample=verify_sample(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
    pe=Path(sample['path']).read_bytes()
    nt,=struct.unpack_from('<I',pe,0x3c)
    count,=struct.unpack_from('<H',pe,nt+6)
    optional,=struct.unpack_from('<H',pe,nt+20)
    base,=struct.unpack_from('<Q',pe,nt+24+24)
    sections=[struct.unpack_from('<4I',pe,nt+24+optional+40*i+8) for i in range(count)]
    def offset(rva,size):
        found=[raw+rva-va for virtual,va,length,raw in sections if va<=rva and rva+size<=va+length]
        if len(found)!=1: raise ValueError('unmapped RVA')
        return found[0]
    def rva(raw):
        found=[va+raw-start for virtual,va,length,start in sections if start<=raw<start+length]
        if len(found)!=1: raise ValueError('unmapped file offset')
        return found[0]
    def read(address,size):
        start=offset(address,size)
        return pe[start:start+size]
    def qword(address): return struct.unpack('<Q',read(address,8))[0]
    def name(address):
        start=offset(address,1);end=pe.find(b'\0',start,start+128)
        if end<start: raise ValueError('long name')
        return pe[start:end].decode('ascii')
    def type_info(address):
        n=qword(address+24)-base
        return dict(rva=hex(address),file_offset=hex(offset(address,0xb0)),bytes=read(address,0xb0).hex(' '),
            name=name(n),name_rva=hex(n),metatype=hex(qword(address+8)-base),
            basicsize=qword(address+32),itemsize=qword(address+40),
            flags=hex(struct.unpack('<I',read(address+0xa8,4))[0]))
    integer=qword(0x7a127f0+0x100)-base
    integer_info=type_info(integer)
    assert integer_info['name']=='int' and integer_info['metatype']=='0x7a15170'
    assert integer_info['basicsize']==24 and integer_info['itemsize']==4
    marker=struct.pack('<Q',base+0x7a15170)
    candidates=[];byte_candidates=[];cursor=0
    while True:
        cursor=pe.find(marker,cursor)
        if cursor<0: break
        try:
            address=rva(cursor)-8
            info=type_info(address)
            if info['name']=='float' and info['basicsize']==24 and info['itemsize']==0:
                candidates.append(info)
            if info['name']=='bytes' and info['basicsize']==33 and info['itemsize']==1:
                byte_candidates.append(info)
        except (ValueError,UnicodeError,struct.error): pass
        cursor+=1
    assert len(candidates)==1, candidates
    assert len(byte_candidates)==1,byte_candidates
    none_type=qword(0x7a0a150+8)-base
    none_info=type_info(none_type)
    assert none_info['name']=='NoneType'
    folder=Path(__file__).parent
    headers={name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
             for name in ['floatobject.h','longintrepr.h','pycore_long.h','bytesobject.h','long-type-initializer.c.txt']}
    result=dict(sample=sample,method='int via Bool_Type.tp_base; unique float type with pinned metatype/name/layout',
        integer=integer_info,float=candidates[0],bytes_type=byte_candidates[0],none_type=none_info,
        none_singleton_rva='0x7a0a150',headers_sha256=headers,
        layout=dict(PyLong=dict(tag_offset=16,digits_offset=24,digit_bytes=4,digit_bits=30,
                         sign_mask=3,count_shift=3,small_int_flag=4),
                    PyFloat=dict(value_offset=16,sizeof=24)),
        digit_bits_proof='PyLong_Type.tp_itemsize=sizeof(digit), native value4; pinned header has digit4 only in 30-bit branch',
        target_executed=False,protected_process_access=False)
    (folder/'scalar-layout-proof.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(integer=integer_info['rva'],float=candidates[0]['rva'],digit_bits=30,
                         sample_sha256=sample['sha256'])))


if __name__=='__main__':main()
