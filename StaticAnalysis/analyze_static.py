# Python | analyze_static.py | Python 3.12, pefile, Capstone | Windows x64, files only.
"""Reproducible PE/RTTI/xref inventory. Does not load or execute the target image."""
import argparse
from bisect import bisect_right
import csv
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).parent / "vendor"))
import pefile
import capstone
from capstone.x86_const import X86_OP_MEM, X86_REG_RIP


def hx(value):
    return f"0x{value:x}"


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def memory_metrics():
    class Counters(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
                  ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage",
                   "QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    psapi=ctypes.WinDLL("psapi",use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
        return dict(error=ctypes.get_last_error())
    return dict(peak_working_set_bytes=counters.PeakWorkingSetSize,working_set_bytes=counters.WorkingSetSize,
                scope="analysis Python process, not game performance")


def local_dependencies(im, out):
    result=[]
    for path in sorted(im.path.parent.glob("*.dll")):
        record=dict(path=str(path),file_size=path.stat().st_size)
        with path.open("rb") as stream:record["sha256"]=hashlib.file_digest(stream,"sha256").hexdigest()
        try:
            pe=pefile.PE(str(path),fast_load=True)
            record.update(machine=hx(pe.FILE_HEADER.Machine),timestamp=hx(pe.FILE_HEADER.TimeDateStamp),
                          preferred_base=hx(pe.OPTIONAL_HEADER.ImageBase))
            pe.parse_data_directories(directories=[1,13])
            record["imports"]=[e.dll.decode("ascii","replace") for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[])]
            record["delay_imports"]=[e.dll.decode("ascii","replace") for e in getattr(pe,"DIRECTORY_ENTRY_DELAY_IMPORT",[])]
            pe.close()
        except (pefile.PEFormatError,ValueError) as error:record["parse_error"]=str(error)
        result.append(record)
    save(out/"local-dependencies.json",result)
    return result


def simple_name(name):
    if re.fullmatch(r"\.\?A[UV][A-Za-z_][A-Za-z_0-9]*(?:@[A-Za-z_][A-Za-z_0-9]*)*@@", name):
        return "::".join(reversed(name[4:-2].split("@")))
    return name


class Image:
    def __init__(self, path):
        self.path = path
        self.data = path.read_bytes()
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.pe = pefile.PE(data=self.data, fast_load=True)
        if self.pe.FILE_HEADER.Machine != 0x8664 or self.pe.OPTIONAL_HEADER.Magic != 0x20b:
            raise ValueError("Expected AMD64 PE32+")
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.sections = []
        for s in self.pe.sections:
            rec = dict(name=s.Name.rstrip(b"\0").decode("ascii", "replace"),
                       rva=s.VirtualAddress, virtual_size=s.Misc_VirtualSize,
                       raw_offset=s.PointerToRawData, raw_size=s.SizeOfRawData,
                       characteristics=hx(s.Characteristics), executable=bool(s.Characteristics & 0x20000000))
            if rec["raw_size"] and rec["raw_offset"] + rec["raw_size"] > len(self.data):
                raise ValueError("Section outside file")
            self.sections.append(rec)
        self.functions = []
        dd = self.pe.OPTIONAL_HEADER.DATA_DIRECTORY[3]
        off = self.offset(dd.VirtualAddress)
        if off is not None and dd.Size and dd.Size % 12 == 0:
            for begin, end, unwind in struct.iter_unpack("<III", self.data[off:off + dd.Size]):
                if begin < end <= self.size and self.is_code(begin) and self.offset(unwind) is not None:
                    self.functions.append((begin, end, unwind))
        self.functions.sort()
        self.starts = [f[0] for f in self.functions]
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        self.md.detail = True

    def section(self, rva):
        return next((s for s in self.sections if s["rva"] <= rva < s["rva"] + max(s["raw_size"], s["virtual_size"])), None)

    def is_code(self, rva):
        s = self.section(rva)
        return bool(s and s["executable"] and rva - s["rva"] < s["raw_size"])

    def offset(self, rva, length=1):
        if 0 <= rva and rva + length <= self.pe.OPTIONAL_HEADER.SizeOfHeaders:
            return rva
        s = self.section(rva)
        if s and 0 <= rva - s["rva"] and rva - s["rva"] + length <= s["raw_size"]:
            return s["raw_offset"] + rva - s["rva"]
        return None

    def rva(self, offset):
        for s in self.sections:
            if s["raw_offset"] <= offset < s["raw_offset"] + s["raw_size"]:
                return s["rva"] + offset - s["raw_offset"]
        return offset if offset < self.pe.OPTIONAL_HEADER.SizeOfHeaders else None

    def unpack(self, fmt, rva):
        off = self.offset(rva, struct.calcsize(fmt))
        if off is None:
            raise ValueError(f"Not file backed: {rva:x}")
        return struct.unpack_from(fmt, self.data, off)

    def string(self, rva, limit=2048):
        off = self.offset(rva)
        if off is None:
            return None
        end = self.data.find(b"\0", off, min(off + limit, len(self.data)))
        if end < 0:
            return None
        raw = self.data[off:end]
        return raw.decode("ascii") if all(32 <= c <= 126 for c in raw) else None

    def function(self, rva):
        i = bisect_right(self.starts, rva) - 1
        return self.functions[i] if i >= 0 and rva < self.functions[i][1] else None

    def instructions(self, start, max_bytes=65536):
        fn = self.function(start)
        end = min(fn[1], start + max_bytes) if fn else start + min(max_bytes, 512)
        off = self.offset(start, end - start)
        return list(self.md.disasm(self.data[off:off + end - start], self.base + start)) if off is not None else []

    def ptr_refs(self, rva, limit=512):
        marker = struct.pack("<Q", self.base + rva)
        refs = []
        for s in self.sections:
            if s["executable"]:
                continue
            at, end = s["raw_offset"], s["raw_offset"] + s["raw_size"]
            while len(refs) < limit:
                at = self.data.find(marker, at, end)
                if at < 0:
                    break
                ref = self.rva(at)
                if ref % 8 == 0:
                    refs.append(ref)
                at += 1
        return refs


def inventory_rtti(im, out):
    descriptors = {}
    for m in re.finditer(rb"\.\?A[UV][\x20-\x7e]{1,2048}\x00", im.data):
        rva = im.rva(m.start())
        if rva is None or rva < 16 or rva % 8:
            continue
        td = rva - 16
        ptr, spare = im.unpack("<QQ", td)
        if not im.base <= ptr < im.base + im.size or spare != 0:
            continue
        name = m.group()[:-1].decode("ascii")
        descriptors[td] = dict(type_descriptor_rva=hx(td), name_rva=hx(rva),
                               decorated_name=name, display_name=simple_name(name),
                               type_info_vftable_rva=hx(ptr - im.base))
    cols = []
    for s in im.sections:
        if s["executable"] or s["name"] != ".rdata":
            continue
        start, end = s["raw_offset"], s["raw_offset"] + s["raw_size"]
        for m in re.finditer(b"\x01\x00\x00\x00", im.data[start:end]):
            off = start + m.start()
            rva = im.rva(off)
            if rva % 4 or off + 24 > end:
                continue
            sig, objoff, cd, td, chd, selfrva = struct.unpack_from("<6I", im.data, off)
            if selfrva != rva or td not in descriptors:
                continue
            try:
                chsig, attributes, count, array = im.unpack("<4I", chd)
                if chsig != 0 or not 1 <= count <= 1024:
                    continue
                bases = []
                for i in range(count):
                    bcd = im.unpack("<I", array + 4*i)[0]
                    btd, contained, md, pd, vd, attrs = im.unpack("<IIiiiI", bcd)
                    if btd not in descriptors:
                        raise ValueError("Invalid base TypeDescriptor")
                    bases.append(dict(name=descriptors[btd]["display_name"], type_descriptor_rva=hx(btd),
                                      descriptor_rva=hx(bcd), contained_bases=contained,
                                      member_displacement=md, vbtable_displacement=pd,
                                      displacement_inside_vbtable=vd, attributes=hx(attrs)))
                if bases[0]["type_descriptor_rva"] != hx(td):
                    continue
            except (ValueError, struct.error):
                continue
            cols.append(dict(rva=hx(rva), type_descriptor_rva=hx(td), name=descriptors[td]["display_name"],
                             object_offset=objoff, construction_displacement=cd,
                             hierarchy_rva=hx(chd), hierarchy_attributes=hx(attributes), bases=bases))
    save(out / "rtti-types.json", list(descriptors.values()))
    save(out / "rtti-hierarchies.json", cols)
    return descriptors, cols


def anchors(im):
    terms = ("GetAllActors", "ActorComponent", "SkeletonComponent", "ICamera", "Asyncore", "PythonAsyncore", "NewSpike")
    found = {}
    stats = {}
    for term in terms:
        matches = list(re.finditer(re.escape(term.encode()), im.data))
        stats[term] = len(matches)
        # Prioritize plain names and binding labels; omit enormous template names from xref analysis.
        for m in matches:
            begin = im.data.rfind(b"\0", max(0, m.start()-512), m.start()) + 1
            end = im.data.find(b"\0", m.end(), m.end()+512)
            if end < 0 or not 0 < end-begin <= 512:
                continue
            raw = im.data[begin:end]
            if not all(32 <= c <= 126 for c in raw):
                continue
            text = raw.decode("ascii")
            if text.startswith(".?A"):
                continue
            # Detailed xrefs for a bounded, explicit list; other bindings remain in the string inventory.
            rva = im.rva(begin)
            if rva is not None:
                found[rva] = dict(rva=hx(rva), file_offset=hx(begin), text=text)
    return found, stats


def xrefs(im, targets):
    result = []
    cache = {}
    pattern = re.compile(rb"[\x48-\x4f][\x8d\x8b\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d][\x00-\xff]{4}")
    for s in im.sections:
        if not s["executable"]:
            continue
        data = im.data[s["raw_offset"]:s["raw_offset"]+s["raw_size"]]
        for m in pattern.finditer(data):
            rva = s["rva"] + m.start()
            target = rva + 7 + struct.unpack_from("<i", m.group(), 3)[0]
            if target not in targets:
                continue
            fn = im.function(rva)
            if not fn or fn[1]-fn[0] > 262144:
                continue
            if fn[0] not in cache:
                cache[fn[0]] = {x.address-im.base: x for x in im.instructions(fn[0], 262144)}
            ins = cache[fn[0]].get(rva)
            if ins is None or ins.size != 7:
                continue
            if not any(o.type == X86_OP_MEM and o.mem.base == X86_REG_RIP and ins.address + ins.size + o.mem.disp - im.base == target for o in ins.operands):
                continue
            result.append(dict(instruction_rva=hx(rva), file_offset=hx(im.offset(rva)),
                               bytes=ins.bytes.hex(" "), instruction=f"{ins.mnemonic} {ins.op_str}",
                               target_rva=hx(target), target=targets[target],
                               function_begin_rva=hx(fn[0]), function_end_rva=hx(fn[1]),
                               boundary_source="PE RUNTIME_FUNCTION; exact instruction boundary verified by Capstone"))
    return result


def xref_windows(im, refs):
    windows=[]
    cache={}
    for ref in refs:
        begin=int(ref["function_begin_rva"],16)
        if begin not in cache:
            cache[begin]=im.instructions(begin,262144)
        insns=cache[begin]
        index=next(i for i,x in enumerate(insns) if x.address-im.base==int(ref["instruction_rva"],16))
        rows=[]
        for ins in insns[max(0,index-8):index+15]:
            row=dict(rva=hx(ins.address-im.base),file_offset=hx(im.offset(ins.address-im.base)),
                     bytes=ins.bytes.hex(" "),mnemonic=ins.mnemonic,operands=ins.op_str)
            for operand in ins.operands:
                if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP:
                    target=ins.address+ins.size+operand.mem.disp-im.base
                    row["rip_target_rva"]=hx(target)
                    row["rip_target_string"]=im.string(target,512)
            rows.append(row)
        windows.append(dict(xref=ref,instructions=rows))
    return windows


def vtables(im, selected, cols):
    result = []
    for col in cols:
        if col["name"] not in selected:
            continue
        for ref in im.ptr_refs(int(col["rva"],16)):
            entries = []
            for i in range(512):
                try:
                    va = im.unpack("<Q", ref+8+i*8)[0]
                except ValueError:
                    break
                if not im.base <= va < im.base+im.size or not im.is_code(va-im.base):
                    break
                entries.append(dict(index=i, slot_rva=hx(ref+8+i*8), function_rva=hx(va-im.base)))
            if entries:
                result.append(dict(name=col["name"], col_rva=col["rva"], col_pointer_rva=hx(ref),
                                   vtable_rva=hx(ref+8), subobject_offset=col["object_offset"],
                                   entries=entries, truncated_at_512=len(entries)==512,
                                   extent_status="candidate run of code pointers; exact C++ virtual method count unproven"))
    return result


def dump_functions(im, requests, out):
    records, text = [], []
    for start, labels in sorted(requests.items()):
        fn = im.function(start)
        insns = im.instructions(start, 16384)
        text.append(f"\n; RVA {hx(start)} | {'; '.join(sorted(labels))}")
        code = []
        for ins in insns[:600]:
            rva = ins.address-im.base
            row = dict(rva=hx(rva), file_offset=hx(im.offset(rva)), bytes=ins.bytes.hex(" "),
                       mnemonic=ins.mnemonic, operands=ins.op_str)
            code.append(row)
            text.append(f"{im.base+rva:016x} RVA {rva:08x} {row['bytes']:<44} {ins.mnemonic} {ins.op_str}")
            if not fn and ins.mnemonic in ("ret", "int3"):
                break
        records.append(dict(start_rva=hx(start), labels=sorted(labels),
                            runtime_function=[hx(v) for v in fn] if fn else None,
                            truncated=len(insns)>600 or bool(fn and fn[1]-start>16384), instructions=code))
    save(out / "function-evidence.json", records)
    (out / "disassembly.txt").write_text("\n".join(text)+"\n", encoding="utf-8")
    return records


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--offsets",type=Path)
    args=p.parse_args()
    start=time.perf_counter(); cpu=time.process_time(); args.out.mkdir(parents=True,exist_ok=True)
    im=Image(args.binary.resolve(strict=True))
    print("Fingerprint and PE parsed", im.sha, flush=True)
    pe=im.pe; pe.parse_data_directories(directories=[0,1,6,13])
    imports=[]
    for kind,entries in (("normal",getattr(pe,"DIRECTORY_ENTRY_IMPORT",[])),("delay",getattr(pe,"DIRECTORY_ENTRY_DELAY_IMPORT",[]))):
        for module in entries:
            symbols=[dict(name=x.name.decode("ascii","replace") if x.name else None, ordinal=x.ordinal,
                          iat_rva=hx(x.address-im.base)) for x in module.imports]
            local=args.binary.parent/module.dll.decode("ascii")
            imports.append(dict(module=module.dll.decode("ascii"),kind=kind,symbols=symbols,
                                adjacent_file=str(local) if local.is_file() else None))
    exports=[dict(name=x.name.decode("ascii","replace") if x.name else None,ordinal=x.ordinal,
                  rva=hx(x.address),kind="code" if im.is_code(x.address) else "data_or_forwarder",
                  forwarder=x.forwarder.decode() if x.forwarder else None)
             for x in getattr(getattr(pe,"DIRECTORY_ENTRY_EXPORT",None),"symbols",[])]
    save(args.out/"imports.json",imports); save(args.out/"exports.json",exports)
    dependencies=local_dependencies(im,args.out)
    tds,cols=inventory_rtti(im,args.out)
    print(f"RTTI: {len(tds)} descriptors, {len(cols)} validated complete object locators",flush=True)
    selected={"Character::Actor","Messiah::ActorComponent","Messiah::SkeletonComponent","Messiah::ISkeletonComponent",
              "Messiah::ICamera","Messiah::IComponent","Messiah::IEntity","Messiah::IObject",
              "Messiah::PythonAsyncoreModule"}
    for td in tds.values():
        if any(f"?$pybase_object_impl@VPy{x}@Messiah@@@Asyncore@@" in td["decorated_name"]
               for x in ("ActorComponent","SkeletonComponent","ICamera","IComponent")):
            selected.add(td["display_name"])
    save(args.out/"core-hierarchies.json",[c for c in cols if c["name"] in selected])
    tables=vtables(im,selected,cols); save(args.out/"core-vtables.json",tables)
    strings,stats=anchors(im); save(args.out/"anchor-strings.json",list(strings.values()))
    targets={r:s["text"] for r,s in strings.items() if (s["text"] in ("GetAllActors","ICamera","ActorComponent","SkeletonComponent","PythonAsyncore") or any(x in s["text"] for x in ("ICamera.ViewMatrix","ICamera.FieldOfView","ICamera.GetOrigin","ICamera.GetScreenPoint","ActorComponent.GetActor","SkeletonComponent.GetBone")))}
    for td in tds.values():
        if td["display_name"] in selected:
            targets[int(td["type_descriptor_rva"],16)]=td["display_name"]+" TypeDescriptor"
    for table in tables:
        if table["name"] in ("Character::Actor","Messiah::ActorComponent","Messiah::SkeletonComponent","Messiah::ICamera"):
            targets[int(table["vtable_rva"],16)]=table["name"]+f" vftable (subobject +{hx(table['subobject_offset'])})"
    refs=xrefs(im,targets); save(args.out/"code-xrefs.json",refs)
    windows=xref_windows(im,refs); save(args.out/"xref-windows.json",windows)
    print(f"Core vtables: {len(tables)}; verified code xrefs: {len(refs)}",flush=True)
    requests={}
    def request(rva,label):requests.setdefault(rva,set()).add(label)
    for ref in refs:request(int(ref["function_begin_rva"],16),"xref: "+ref["target"])
    for window in windows:
        if window["xref"]["target"]=="GetAllActors":
            seen_string=False
            for row in window["instructions"]:
                if row.get("rip_target_string")=="GetAllActors":seen_string=True; continue
                candidate=int(row.get("rip_target_rva","0"),16)
                if seen_string and row["mnemonic"]=="lea" and im.is_code(candidate):
                    request(candidate,"candidate callback stored after GetAllActors binding; validate +8 store in xref window")
                    for ins in im.instructions(candidate):
                        if ins.mnemonic=="call" and len(ins.operands)==1 and ins.operands[0].type==capstone.x86_const.X86_OP_IMM:
                            callee=ins.operands[0].imm-im.base
                            if im.is_code(callee):request(callee,"direct callee of GetAllActors callback; semantic name unproven")
                    break
    for table in tables:
        if table["name"] in ("Character::Actor","Messiah::ActorComponent","Messiah::SkeletonComponent","Messiah::ICamera"):
            for slot in table["entries"][:6]:request(int(slot["function_rva"],16),table["name"]+f" vslot {slot['index']}")
    for s in strings.values():
        if s["text"] in ("ICamera.ViewMatrix","ICamera.FieldOfView"):
            for ref in im.ptr_refs(int(s["rva"],16)):
                for delta in (32,40,48,56,64):
                    va=im.unpack("<Q",ref+delta)[0]
                    if im.base<=va<im.base+im.size and im.is_code(va-im.base):
                        request(va-im.base,s["text"]+f" metadata pointer at {hx(ref+delta)} (role initially unproven)")
    # Export names are independent linker evidence; select Python initialization/query functions only.
    for exp in exports:
        if exp["name"] in ("Py_Initialize","Py_GetVersion","PyObject_GetAttrString","PyModule_Create2"):
            request(int(exp["rva"],16),"export: "+exp["name"])
    funcs=dump_functions(im,requests,args.out)
    debug=[]
    for entry in getattr(pe,"DIRECTORY_ENTRY_DEBUG",[]):
        rec=dict(type=entry.struct.Type,timestamp=hx(entry.struct.TimeDateStamp),size=entry.struct.SizeOfData)
        if entry.struct.Type==2:
            off=entry.struct.PointerToRawData; raw=im.data[off:off+entry.struct.SizeOfData]
            rec.update(signature=raw[:4].decode("ascii","replace"),raw_hex=raw.hex(),
                       pdb_path=raw[24:].split(b"\0")[0].decode("utf8","replace") if raw[:4]==b"RSDS" else None)
        debug.append(rec)
    external=[]
    if args.offsets:
        supplied=json.loads(args.offsets.read_text(encoding="utf-8-sig"))
        for name,value in supplied.get("offsets",{}).items():
            try:n=int(str(value),0)
            except ValueError:continue
            external.append(dict(name=name,value=hx(n),as_main_image_rva_inside=0<=n<im.size,
                                 status="UNVALIDATED_NO_MODULE_OR_VERSION"))
        save(args.out/"external-offsets-unvalidated.json",external)
    unchanged=hashlib.sha256(args.binary.read_bytes()).hexdigest()==im.sha
    if not unchanged:raise RuntimeError("Binary changed during analysis; discard results")
    report=dict(generated_utc=datetime.now(timezone.utc).isoformat(),binary=str(im.path),sha256=im.sha,
                file_size=len(im.data),pe_timestamp_raw=hx(pe.FILE_HEADER.TimeDateStamp),
                pe_timestamp_utc=datetime.fromtimestamp(pe.FILE_HEADER.TimeDateStamp,timezone.utc).isoformat(),
                timestamp_caveat="Header declaration, not independently authenticated build date; check REPRO debug entry",
                image_base_preferred=hx(im.base),size_of_image=hx(im.size),entry_point_rva=hx(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
                machine=hx(pe.FILE_HEADER.Machine),sections=im.sections,debug=debug,
                tools=dict(python=sys.version,pefile=pefile.__version__,capstone_package=importlib.metadata.version("capstone"),capstone_engine=capstone.__version__),
                counts=dict(rtti_type_descriptors=len(tds),complete_object_locators=len(cols),
                            runtime_function_entries=len(im.functions),imports_modules=len(imports),exports=len(exports),
                            adjacent_dlls_inventoried=len(dependencies),
                            core_vtables=len(tables),code_xrefs=len(refs),dumped_functions=len(funcs)),
                anchor_occurrences=stats,binary_unchanged_after_analysis=unchanged,
                scope="STATIC_FILE_ANALYSIS",runtime_validation_performed=False,
                limits=["No inferred field names solely from displacement values", "RTTI inventory is not a full source class reconstruction",
                        "xrefs cover selected RIP-relative 64-bit LEA/MOV forms only", "No claim that strings designate live actors",
                        "Vtable extents are candidate executable pointer runs; capped at 512", "Unknown engine reflection metadata layouts not assumed"],
                measurements=dict(wall_seconds=round(time.perf_counter()-start,3),cpu_seconds=round(time.process_time()-cpu,3),**memory_metrics()))
    save(args.out/"summary.json",report)
    print(json.dumps(dict(report=str(args.out/"summary.json"),**report["counts"],measurements=report["measurements"])),flush=True)


if __name__=="__main__":main()
