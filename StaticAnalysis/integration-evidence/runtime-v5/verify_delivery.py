# Python | runtime-v5/verify_delivery.py | Python 3.12+ | PE bytes, source/test binding and prior artifact integrity.
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ExternalCore.build import verify_sample


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_rows(value):
    if isinstance(value, dict):
        if {"rva", "file_offset", "bytes"} <= value.keys():
            yield value
        for item in value.values(): yield from evidence_rows(item)
    elif isinstance(value, list):
        for item in value: yield from evidence_rows(item)


def integer(value):
    return int(value,16) if isinstance(value,str) else value


def main():
    sample = verify_sample(r"E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe")
    pe = Path(sample["path"]).read_bytes()
    nt, = struct.unpack_from("<I",pe,0x3C)
    count, = struct.unpack_from("<H",pe,nt+6)
    optional, = struct.unpack_from("<H",pe,nt+20)
    sections = [struct.unpack_from("<4I",pe,nt+24+optional+40*i+8) for i in range(count)]
    def offset(rva,size):
        found = [raw+rva-va for virtual,va,length,raw in sections if va <= rva and rva+size <= va+length]
        if len(found) != 1: raise ValueError(f"unbacked/ambiguous RVA {rva:#x}")
        return found[0]
    def read(rva,size):
        start = offset(rva,size)
        return pe[start:start+size]
    def unpack(fmt,rva): return struct.unpack(fmt,read(rva,struct.calcsize(fmt)))
    def string(rva):
        start = offset(rva,1)
        end = pe.find(b"\0",start,start+1024)
        assert end >= start
        return pe[start:end].decode("ascii")
    selected = []
    for name,col,td in [("Messiah::ICamera",0x6E1E1B8,0x7DE5D50),
                        ("Messiah::IGameplay",0x6E7A3A0,0x7E35098),
                        ("Messiah::ClientPlayer",0x6EA2828,0x7E57120)]:
        fields = unpack("<6I",col)
        assert fields[0] == 1 and fields[3] == td and fields[5] == col
        raw_name = string(td+16)
        assert raw_name == ".?AV"+name.split("::")[1]+"@Messiah@@"
        selected.append(dict(name=name,col_rva=hex(col),type_descriptor_rva=hex(td),raw_name=raw_name,
            file_offset=hex(offset(col,24)),bytes=read(col,24).hex()))
    for name,rva in [("dict",0x7A19900),("str",0x7A16E10),("tuple",0x7A18CE0),
                     ("type",0x7A15170),("bool",0x7A127F0)]:
        address, = unpack("<Q",rva+24)
        assert string(address-0x140000000) == name
        selected.append(dict(name=name,type_rva=hex(rva),name_rva=hex(address-0x140000000)))
    assert unpack("<Q",0x7A15170+8)[0] == 0x140000000+0x7A15170
    for rva,tag,digit in [(0x7A12990,1,0),(0x7A129B0,8,1)]:
        assert unpack("<Q",rva+8)[0] == 0x140000000+0x7A127F0
        assert unpack("<Q",rva+16)[0] == tag and unpack("<I",rva+24)[0] == digit

    record_count,unique = 0,set()
    folder_counts = {}
    for folder in ["coordinate-bridge-v5","python-owner-v5","gameplay-classifier-v5"]:
        local = 0
        for path in (ROOT/"StaticAnalysis/integration-evidence"/folder).glob("*.json"):
            for row in evidence_rows(json.loads(path.read_text(encoding="utf-8"))):
                if row["file_offset"] is None: continue
                data = bytes.fromhex(row["bytes"])
                if not data: continue
                rva,reported = integer(row["rva"]),integer(row["file_offset"])
                assert offset(rva,len(data)) == reported and read(rva,len(data)) == data, (path.name,row["rva"])
                record_count += 1;local += 1;unique.add((rva,len(data)))
        folder_counts[folder] = local
    tests = json.loads((ROOT/"reports/tests-v5/summary.json").read_text(encoding="utf-8"))
    assert tests["status"] == "PASS" and tests["tests_run"] >= 71 and not tests["skipped"]
    for relative,expected in tests["source_sha256"].items():
        assert digest(ROOT/relative) == expected, relative
    baseline = json.loads((ROOT/"StaticAnalysis/audit-v4/artifact-sha256.json").read_text())
    for relative,expected in baseline.items():
        assert digest(ROOT/"StaticAnalysis"/relative) == expected, relative
    result = dict(status="PASS",date="2026-11-01",sample=sample,types=selected,
        checked_byte_records=record_count,distinct_byte_ranges=len(unique),records_by_folder=folder_counts,
        tested_sources_unchanged=len(tests["source_sha256"]),tests_run=tests["tests_run"],
        v4_manifest_files_unchanged=len(baseline),protected_game_access=False,system_input_events_sent=False,
        scope="on-disk bytes and source/test hashes; not live gameplay, universal semantic or full CFG proof")
    target = Path(__file__).with_name("delivery-verification.json")
    target.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:value for key,value in result.items() if key != "types"}))


if __name__ == "__main__": main()
