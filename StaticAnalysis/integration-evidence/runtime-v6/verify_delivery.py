# Python | runtime-v6/verify_delivery.py | Python 3.12+ | disk evidence and tested-source integrity, no target execution.
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from ExternalCore.build import verify_sample
from ExternalCore.predicate_spec import BASE_IS_ENEMY

OUTPUT=Path(__file__).with_name('delivery-verification.json')
FOLDERS=['coordinate-bridge-v5','python-owner-v5','gameplay-classifier-v5',
         'combat-state-v6','local-player-v6','native-properties-v6','predicate-code-v6','python-values-v6']


def require(value,label):
    if not value:raise ValueError(label)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(value):
    if isinstance(value,dict):
        if {'rva','file_offset','bytes'} <= value.keys():yield value
        for child in value.values():yield from rows(child)
    elif isinstance(value,list):
        for child in value:yield from rows(child)


def payload_rows(value):
    if isinstance(value,dict):
        if {'index','compressed_sha256','decoded_sha256'} <= value.keys():yield value
        for child in value.values():yield from payload_rows(child)
    elif isinstance(value,list):
        for child in value:yield from payload_rows(child)


def decode_payload(raw):
    require(len(raw)>=8 and raw[:2]==b'\xe2\x06','unsupported packaged stream')
    transformed=bytearray(raw);prefix=min(128-((len(raw)-8)%37),len(raw))
    for index in range(prefix):transformed[index]^=0x9A
    end=len(raw) if prefix==len(raw) else len(raw)-8
    decoder=zlib.decompressobj();decoded=decoder.decompress(bytes(transformed[:end]),8*1024*1024+1)
    require(len(decoded)<=8*1024*1024 and decoder.eof and not decoder.unconsumed_tail
            and not decoder.unused_data,'incomplete/excessive packaged stream')
    return decoded


def main():
    OUTPUT.write_text('{"status":"RUNNING"}\n',encoding='utf-8')
    try:
        sample=verify_sample(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
        pe=Path(sample['path']).read_bytes();nt=struct.unpack_from('<I',pe,0x3C)[0]
        count=struct.unpack_from('<H',pe,nt+6)[0];optional=struct.unpack_from('<H',pe,nt+20)[0]
        sections=[struct.unpack_from('<4I',pe,nt+24+optional+40*i+8) for i in range(count)]
        def offset(rva,length):
            found=[raw+rva-va for virtual,va,size,raw in sections if va<=rva and rva+length<=va+size]
            require(len(found)==1,f'unbacked/ambiguous RVA {rva:#x}')
            return found[0]
        def integer(value):return int(value,16) if isinstance(value,str) else value
        by_folder={};unique=set();manifests={};payloads={}
        evidence=ROOT/'StaticAnalysis/integration-evidence'
        for folder in FOLDERS:
            checked=0
            for path in sorted((evidence/folder).rglob('*.json')):
                payload=json.loads(path.read_text(encoding='utf-8'))
                if folder.endswith('v6'):
                    for row in payload_rows(payload):
                        require(type(row['index']) is int,'unsupported resource index')
                        expected=(row['compressed_sha256'],row['decoded_sha256'])
                        require(row['index'] not in payloads or payloads[row['index']]==expected,
                                'conflicting resource hashes')
                        payloads[row['index']]=expected
                for row in rows(payload):
                    if row['file_offset'] is None:continue
                    raw=bytes.fromhex(row['bytes'])
                    if not raw:continue
                    rva,reported=integer(row['rva']),integer(row['file_offset'])
                    actual=offset(rva,len(raw))
                    require(actual==reported and pe[actual:actual+len(raw)]==raw,
                            f'PE byte mismatch: {path.relative_to(ROOT)} {rva:#x}')
                    checked+=1;unique.add((rva,len(raw)))
                if path.name=='artifact-manifest.json':
                    require(isinstance(payload,dict),'unsupported manifest format')
                    if 'artifacts' in payload:
                        require(payload['target_sha256']==sample['sha256'],'manifest sample differs')
                        entries={entry['path']:entry['sha256'] for entry in payload['artifacts']}
                    else:entries=payload
                    for relative,expected in entries.items():
                        require(digest(path.parent/relative)==expected,f'evidence changed: {path.parent/relative}')
                    manifests[str(path.relative_to(ROOT)).replace('\\','/')]=len(entries)
            by_folder[folder]=checked
        install=Path(sample['path']).parents[3]
        index=(install/'Resources.mpkinfo').read_bytes()
        require(hashlib.sha256(index).hexdigest()=='bb3782da03b95d66451a598add8fe0923405be0dde53a8844b2f8bc107a6ced3',
                'resource index changed')
        version,entries=struct.unpack_from('<II',index)
        require(version==4 and len(index)==8+24*entries+16,'resource index layout differs')
        aggregate=0
        for item,(compressed_hash,decoded_hash) in sorted(payloads.items()):
            require(0<=item<entries,'resource index outside table')
            ident,start,size,flags=struct.unpack_from('<QQII',index,8+24*item)
            require(not flags&1 and 8<=size<=1024*1024,'unsupported/excessive indexed payload')
            package=flags>>1
            path=install/('Resources'+('' if package==0 else str(package))+'.mpk')
            with path.open('rb') as stream:stream.seek(start);raw=stream.read(size)
            require(len(raw)==size and hashlib.sha256(raw).hexdigest()==compressed_hash,f'packaged bytes changed: {item}')
            decoded=decode_payload(raw);aggregate+=len(decoded)
            require(aggregate<=128*1024*1024,'aggregate decode budget exhausted')
            require(hashlib.sha256(decoded).hexdigest()==decoded_hash,f'decoded bytes changed: {item}')
        scalar=json.loads((evidence/'python-values-v6/scalar-layout-proof.json').read_text())
        for name,expected in scalar['headers_sha256'].items():
            require(digest(evidence/'python-values-v6'/name)==expected,f'scalar source changed: {name}')
        baseline=json.loads((evidence/'predicate-code-v6/baseline-is-enemy.json').read_text())
        tables=json.loads((evidence/'predicate-code-v6/opcode-tables.json').read_text())
        require(BASE_IS_ENEMY['canonical']==baseline['canonical'],'generated instruction spec differs')
        require(BASE_IS_ENEMY['canonical_sha256']==baseline['canonical_sha256'],'generated fingerprint differs')
        require(BASE_IS_ENEMY['metadata']==baseline['required_semantic_fields'],'generated semantic spec differs')
        require(BASE_IS_ENEMY['code_hex']==baseline['code_hex'],'generated original code differs')
        for name,field in [('_PyOpcode_Caches','caches_hex'),('_PyOpcode_Deopt','deopt_hex')]:
            values=bytes(tables[name]['values'])
            require(bytes.fromhex(BASE_IS_ENEMY[field])==values,'generated opcode map differs')
            matches=tables[name]['native_exact_matches']
            require(len(matches)==1,'opcode table has no unique native match')
            rva=integer(matches[0]['rva'])
            start=offset(rva,256)
            require(pe[start:start+256]==values,'opcode map bytes differ from the PE')
        tests=json.loads((ROOT/'reports/tests-v6/summary.json').read_text())
        require(tests['status']=='PASS' and tests['tests_run']==108 and not tests['skipped'],'test run is incomplete')
        for relative,expected in tests['source_sha256'].items():
            require(digest(ROOT/relative)==expected,f'tested source changed: {relative}')
        sealed=json.loads((ROOT/'StaticAnalysis/audit-v4/artifact-sha256.json').read_text())
        for relative,expected in sealed.items():
            require(digest(ROOT/'StaticAnalysis'/relative)==expected,f'sealed V4 artifact changed: {relative}')
        native=[event for event in tests['tests'] if event['id'].startswith(tuple(tests['native_required_groups']))]
        require(len(native)==9 and all(event['status']=='passed' for event in native),'native integration coverage incomplete')
        result=dict(status='PASS',date='2026-11-01',sample=sample,checked_byte_records=sum(by_folder.values()),
            distinct_byte_ranges=len(unique),records_by_folder=by_folder,artifact_manifests=manifests,
            tested_sources_unchanged=len(tests['source_sha256']),tests_run=tests['tests_run'],native_tests=len(native),
            v4_manifest_files_unchanged=len(sealed),generated_predicate_spec='MATCH',
            mpk_payloads_rechecked=len(payloads),mpk_decoded_bytes=aggregate,
            protected_game_access=False,target_code_executed=False,system_input_events_sent=False,
            gameplay_validated=False,publisher_certification=False,
            scope='selected on-disk bytes, manifests, and current test/source binding; not live type/dispatch/lifetime proof')
        OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))
        return 0
    except Exception as exc:
        OUTPUT.write_text(json.dumps(dict(status='FAIL',error_type=type(exc).__name__,error=str(exc)),indent=2)+'\n')
        raise


if __name__=='__main__':raise SystemExit(main())
