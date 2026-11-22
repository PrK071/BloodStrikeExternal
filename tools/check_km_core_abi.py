#!/usr/bin/env python3
# Python | tools/check_km_core_abi.py | Python 3.12+ | no driver, no elevation
"""Static consistency checker for the km_core ABI.

Cross-checks three independent descriptions of the same contract:

  1. the driver source   (km_core.c: structs, C_ASSERTs, CTL_CODE, names);
  2. the user-mode client (tools/km_core_client.py: ctypes layout, constants);
  3. the linked binary    (km_core.sys: PE headers, imports, strings).

A name match alone is never treated as proof: sizes, offsets and alignment are
recomputed from the C declarations with an independent layout engine and
compared against ctypes, and the IOCTL values are recomputed from the CTL_CODE
arguments instead of being compared textually.

Exit codes: 0 = consistent, 1 = divergence, 2 = setup problem.

Usage:
    python tools/check_km_core_abi.py
    python tools/check_km_core_abi.py --driver-dir C:\\path\\to\\km_core
    python tools/check_km_core_abi.py --skip-binary
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
# Local project layout: the driver tree lives outside this repository.
# Override with --driver-dir or the KM_CORE_DIR environment variable.
DEFAULT_DRIVER_DIR = Path(os.environ.get("KM_CORE_DIR", Path.home() / "km_cheat" / "km_core"))

# Hashes of the approved artifacts. A mismatch is a hard failure: it means the
# reviewed source changed without a new review. Update only after approval.
# The two source hashes are hard gates. The binary hash is reported, not gated,
# because every rebuild rewrites the PE timestamp; the binary's content is
# checked structurally instead (sections, imports, strings, W^X).
APPROVED = {
    "driver_source": "99C031ADF33DA425A5DDA4541AA34EAFFB1EE13A513F3CD9211CF20650C1A18B",
    "client_source": "15D7A03303267C5BAF92A28805F085DB0F70A25A9E30DF426F667404CBE910B3",
}

C_TYPE_SIZE = {"ULONG32": 4, "LONG": 4, "ULONG64": 8, "LONG64": 8}
C_TYPE_SIGNED = {"ULONG32": False, "LONG": True, "ULONG64": False, "LONG64": True}
CTYPES_SIZE = {ctypes.c_uint32: 4, ctypes.c_int32: 4, ctypes.c_uint64: 8, ctypes.c_int64: 8}
CTYPES_SIGNED = {ctypes.c_uint32: False, ctypes.c_int32: True,
                 ctypes.c_uint64: False, ctypes.c_int64: True}

CTL_DEVICE = {"FILE_DEVICE_UNKNOWN": 0x22}
CTL_METHOD = {
    "METHOD_BUFFERED": 0,
    "METHOD_IN_DIRECT": 1,
    "METHOD_OUT_DIRECT": 2,
    "METHOD_NEITHER": 3,
}
CTL_ACCESS = {
    "FILE_ANY_ACCESS": 0,
    "FILE_READ_DATA": 0x1,
    "FILE_WRITE_DATA": 0x2,
    "FILE_READ_DATA | FILE_WRITE_DATA": 0x3,
}

FORBIDDEN_APIS = [
    "MmCopyVirtualMemory", "PsGetProcessPeb", "PsProcessType", "PsLookupProcessByProcessId",
    "MmMapViewInSystemSpace", "ZwCreateSection", "PsCreateSystemThread",
    "KeStackAttachProcess", "ObOpenObjectByPointer", "ZwOpenProcess",
]

# Imports audited in Etapa 3: 5 direct + 30 from wdmsec/BufferOverflowK.
EXPECTED_IMPORTS = {
    "ExAllocatePoolWithTag", "ExFreePoolWithTag", "IoCreateDevice", "IoCreateSymbolicLink",
    "IoDeleteDevice", "IoDeleteSymbolicLink", "IoDeviceObjectType", "IoIsWdmVersionAvailable",
    "IofCompleteRequest", "KeBugCheckEx", "MmGetSystemRoutineAddress", "ObOpenObjectByPointer",
    "RtlAbsoluteToSelfRelativeSD", "RtlAddAccessAllowedAce", "RtlCreateSecurityDescriptor",
    "RtlFreeUnicodeString", "RtlGetDaclSecurityDescriptor", "RtlGetGroupSecurityDescriptor",
    "RtlGetOwnerSecurityDescriptor", "RtlGetSaclSecurityDescriptor", "RtlInitUnicodeString",
    "RtlLengthSecurityDescriptor", "RtlLengthSid", "RtlSetDaclSecurityDescriptor",
    "SeCaptureSecurityDescriptor", "SeExports", "ZwClose", "ZwCreateKey", "ZwOpenKey",
    "ZwQueryValueKey", "ZwSetSecurityObject", "ZwSetValueKey", "_snwprintf", "_wcsnicmp",
    "wcschr",
}

FAILS: list[str] = []
NOTES: list[str] = []


def ok(msg: str) -> None:
    print(f"  [ok]   {msg}")


def fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"  [FAIL] {msg}")


def note(msg: str) -> None:
    NOTES.append(msg)
    print(f"  [note] {msg}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 1. Driver source
# --------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_driver(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    src = strip_comments(raw)
    joined = src.replace("\\\r\n", " ").replace("\\\n", " ")

    out: dict = {"raw": raw, "joined": joined}

    m = re.search(r"#define\s+KM_ABI_VERSION\s+(\d+)", joined)
    out["abi"] = int(m.group(1)) if m else None

    m = re.search(r'#define\s+KM_DEVICE_NAME\s+L"((?:[^"\\]|\\.)*)"', raw)
    out["device"] = m.group(1).replace("\\\\", "\\") if m else None
    m = re.search(r'#define\s+KM_SYMLINK_NAME\s+L"((?:[^"\\]|\\.)*)"', raw)
    out["symlink"] = m.group(1).replace("\\\\", "\\") if m else None
    m = re.search(r'#define\s+KM_DEVICE_SDDL\s+L"((?:[^"\\]|\\.)*)"', raw)
    out["sddl"] = m.group(1) if m else None

    # structs
    out["structs"] = {}
    for sm in re.finditer(r"typedef\s+struct\s+_(\w+)\s*\{(.*?)\}\s*(\w+)[^;]*;", src, re.S):
        tag, body, name = sm.group(1), sm.group(2), sm.group(3)
        fields = [(t, f) for t, f in
                  re.findall(r"^\s*(ULONG32|ULONG64|LONG64|LONG)\s+(\w+)\s*;", body, re.M)]
        out["structs"][name] = {"tag": tag, "fields": fields}

    # IOCTLs: name -> (device, function, method, access)
    out["ioctls"] = {}
    for m in re.finditer(
        r"#define\s+(IOCTL_\w+)\s+CTL_CODE\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*(\w+)\s*,\s*([^)]+?)\)",
        joined,
    ):
        out["ioctls"][m.group(1)] = (m.group(2), int(m.group(3), 0), m.group(4), m.group(5).strip())

    # C_ASSERTs
    out["assert_size"] = {
        n: int(v, 0)
        for n, v in re.findall(r"C_ASSERT\(\s*sizeof\((\w+)\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)", joined)
    }
    out["assert_off"] = {
        (n, f): int(v, 0)
        for n, f, v in re.findall(
            r"C_ASSERT\(\s*FIELD_OFFSET\((\w+),\s*(\w+)\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)",
            joined,
        )
    }
    return out


def c_layout(fields: list[tuple[str, str]]) -> tuple[list[tuple[str, int, int]], int, int]:
    """Independent x64 natural layout: returns (name, offset, size), total, align."""
    off, align, placed = 0, 1, []
    for ctype, name in fields:
        size = C_TYPE_SIZE.get(ctype)
        if size is None:
            raise ValueError(f"unknown C type: {ctype}")
        off = (off + size - 1) // size * size
        placed.append((name, off, size))
        off += size
        align = max(align, size)
    total = (off + align - 1) // align * align
    return placed, total, align


def ctl_code(device: str, function: int, method: str, access: str) -> int:
    if device not in CTL_DEVICE or method not in CTL_METHOD or access not in CTL_ACCESS:
        raise ValueError(f"unknown CTL_CODE component: {device}/{method}/{access}")
    return (
        (CTL_DEVICE[device] << 16)
        | (CTL_ACCESS[access] << 14)
        | (function << 2)
        | CTL_METHOD[method]
    )


# --------------------------------------------------------------------------
# 2. Client
# --------------------------------------------------------------------------

def load_client(path: Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("km_core_client_checked", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # runs _check_layout(), failing loudly
    return module


# --------------------------------------------------------------------------
# 3. Binary
# --------------------------------------------------------------------------

def check_binary(path: Path) -> None:
    try:
        import pefile
    except ImportError:
        fail("pefile is required for binary checks (install it or pass --skip-binary)")
        return

    pe = pefile.PE(str(path), fast_load=False)
    oh = pe.OPTIONAL_HEADER

    print("\n[3] binary")

    if pe.FILE_HEADER.Machine == 0x8664:
        ok("machine = 0x8664 (x64)")
    else:
        fail(f"machine = 0x{pe.FILE_HEADER.Machine:X}, expected 0x8664")

    if oh.Subsystem == 1:
        ok("subsystem = NATIVE (1)")
    else:
        fail(f"subsystem = {oh.Subsystem}, expected 1")

    expected_dll = 0x1E0  # DYNAMIC_BASE|FORCE_INTEGRITY|NX_COMPAT|HIGH_ENTROPY_VA
    if oh.DllCharacteristics == expected_dll:
        ok(f"DllCharacteristics = 0x{oh.DllCharacteristics:X}")
    else:
        fail(f"DllCharacteristics = 0x{oh.DllCharacteristics:X}, expected 0x{expected_dll:X}")

    reloc = oh.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_BASERELOC"]]
    if reloc.VirtualAddress and reloc.Size:
        ok(f"relocations present (RVA 0x{reloc.VirtualAddress:X}, {reloc.Size} bytes)")
    else:
        fail("no relocation section (image is not relocatable)")

    text = next((s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text"), None)
    if text is None:
        fail(".text section missing")
    elif text.VirtualAddress <= oh.AddressOfEntryPoint < text.VirtualAddress + text.Misc_VirtualSize:
        ok(f"entry point RVA 0x{oh.AddressOfEntryPoint:X} inside .text")
    else:
        fail("entry point outside .text")

    # W^X: no section may be writable and executable at the same time
    bad = [s.Name.rstrip(b"\x00").decode() for s in pe.sections
           if (s.Characteristics & 0x80000000) and (s.Characteristics & 0x20000000)]
    if bad:
        fail(f"W+X sections: {bad}")
    else:
        ok("no writable+executable section (W^X)")

    data = next((s for s in pe.sections if s.Name.rstrip(b"\x00") == b".data"), None)
    if data is None:
        fail(".data section missing")
    elif data.Characteristics & 0x20000000:
        fail(".data is executable")
    else:
        ok(".data present and not executable")

    # imports
    dlls, names = [], set()
    for d in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dlls.append(d.dll.decode().lower())
        names.update(e.name.decode() for e in d.imports if e.name)
    if dlls == ["ntoskrnl.exe"]:
        ok("single dependency: ntoskrnl.exe")
    else:
        fail(f"unexpected dependencies: {dlls}")

    missing = EXPECTED_IMPORTS - names
    extra = names - EXPECTED_IMPORTS
    if missing:
        fail(f"expected imports missing: {sorted(missing)}")
    if extra:
        fail(f"unaudited imports: {sorted(extra)}")
    if not missing and not extra:
        ok(f"{len(names)} imports, exactly the audited set")

    # The exact-set comparison above is the real gate: an import is only
    # accepted if it belongs to the audited list. ObOpenObjectByPointer is in
    # that list because wdmsec applies the device SD through it, not because
    # km_core opens any object by pointer.
    if "ObOpenObjectByPointer" in names:
        note("ObOpenObjectByPointer comes from wdmsec (IopDevObjApplyPostCreationSettings)")

    if getattr(pe, "DIRECTORY_ENTRY_EXPORT", None):
        fail("binary exports symbols")
    else:
        ok("no exports")

    blob = path.read_bytes()
    if "\\Device\\KmCore".encode("utf-16-le") in blob:
        ok("\\Device\\KmCore string present (UTF-16)")
    else:
        fail("device name string missing")
    residues = [r for r in ("KmRwShared", "BaseNamedObjects", "km_rw")
                if r.encode("utf-16-le") in blob or r.encode("ascii") in blob]
    if residues:
        fail(f"km_rw residues in binary: {residues}")
    else:
        ok("no km_rw residue")

    ds = oh.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_LOAD_CONFIG"]]
    if ds.VirtualAddress:
        ok(f"load config present (RVA 0x{ds.VirtualAddress:X})")
    else:
        note("load config missing (no GS cookie in this image)")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--driver-dir", type=Path, default=DEFAULT_DRIVER_DIR)
    ap.add_argument("--client", type=Path, default=REPO_ROOT / "tools" / "km_core_client.py")
    ap.add_argument("--binary", type=Path, default=None,
                    help="PE to inspect (default: <driver-dir>/km_core.sys)")
    ap.add_argument("--skip-binary", action="store_true")
    args = ap.parse_args(argv)

    driver_c = args.driver_dir / "km_core.c"
    binary = args.binary if args.binary is not None else args.driver_dir / "km_core.sys"

    print("km_core ABI checker")
    print(f"  driver : {driver_c}")
    print(f"  client : {args.client}")
    print(f"  binary : {'(skipped)' if args.skip_binary else binary}")

    for path in (driver_c, args.client):
        if not path.is_file():
            print(f"\nsetup error: missing file: {path}", file=sys.stderr)
            return 2

    print("\n[0] approved source hashes")
    d_hash, c_hash = sha256(driver_c), sha256(args.client)
    for label, got, want in (("driver", d_hash, APPROVED["driver_source"]),
                             ("client", c_hash, APPROVED["client_source"])):
        if got.lower() == want.lower():
            ok(f"{label} {got[:16]}...")
        else:
            fail(f"{label} {got} != approved {want}")

    drv = parse_driver(driver_c)
    try:
        cli = load_client(args.client)
    except Exception as exc:  # _check_layout() aborts on a broken layout
        fail(f"client failed to load (layout guard): {exc}")
        return 1

    print("\n[1] driver declarations")
    for key in ("device", "symlink", "sddl", "abi"):
        if drv.get(key):
            ok(f"{key} = {drv[key]!r}")
        else:
            fail(f"declaration not found: {key}")
    if not drv["structs"]:
        fail("no struct found in driver source")
    if not drv["ioctls"]:
        fail("no IOCTL found in driver source")

    print("\n[2] ABI: driver <-> client")
    if drv["abi"] == getattr(cli, "ABI_VERSION", None):
        ok(f"KM_ABI_VERSION = {drv['abi']}")
    else:
        fail(f"ABI driver={drv['abi']} client={getattr(cli, 'ABI_VERSION', None)}")

    # IOCTLs: recomputed from the macro arguments, never compared by name
    for name, (dev, fn, method, access) in sorted(drv["ioctls"].items()):
        try:
            computed = ctl_code(dev, fn, method, access)
        except ValueError as exc:
            fail(f"{name}: {exc}")
            continue
        client_value = getattr(cli, name, None)
        if client_value is None:
            fail(f"{name}: missing in client")
        elif client_value != computed:
            fail(f"{name}: client 0x{client_value:06X} != driver 0x{computed:06X}")
        else:
            ok(f"{name} = 0x{computed:06X}")

    # structs: independent layout engine vs ctypes
    client_structs = sorted(
        n for n in dir(cli) if n.startswith("KM_") and hasattr(getattr(cli, n), "_fields_")
    )
    for sname in client_structs:
        info = drv["structs"].get(sname)
        if info is None:
            fail(f"{sname}: present in client, missing in driver")
            continue
        try:
            placed, total, align = c_layout(info["fields"])
        except ValueError as exc:
            fail(f"{sname}: {exc}")
            continue

        cls = getattr(cli, sname)
        c_names = [n for n, _ in cls._fields_]
        d_names = [name for _ctype, name in info["fields"]]
        if c_names != d_names:
            fail(f"{sname}: fields/order differ driver={d_names} client={c_names}")
            continue
        if ctypes.sizeof(cls) != total:
            fail(f"{sname}: sizeof client={ctypes.sizeof(cls)} driver={total}")
            continue
        if ctypes.alignment(cls) != align:
            fail(f"{sname}: alignment client={ctypes.alignment(cls)} driver={align}")
            continue

        field_ok = True
        for (name, off, size), (c_type, _), (cname, py_type) in zip(
                placed, info["fields"], cls._fields_):
            csize = CTYPES_SIZE.get(py_type)
            coff = getattr(cls, name).offset
            if csize != size or coff != off:
                fail(f"{sname}.{name}: client off={coff} size={csize} / driver off={off} size={size}")
                field_ok = False
                continue
            # same size, but signedness still changes the meaning of the value
            if CTYPES_SIGNED.get(py_type) != C_TYPE_SIGNED.get(c_type):
                fail(f"{sname}.{name}: signedness client={CTYPES_SIGNED.get(py_type)} "
                     f"/ driver={C_TYPE_SIGNED.get(c_type)} ({c_type})")
                field_ok = False
        if field_ok:
            ok(f"{sname}: 0x{total:X}, alignment {align}, {len(placed)} fields")

        # C_ASSERTs: the ones present must match; missing ones are noted
        if drv["assert_size"].get(sname) != total:
            fail(f"{sname}: missing or wrong C_ASSERT(sizeof)")
        for name, off, _ in placed:
            declared = drv["assert_off"].get((sname, name))
            if declared is None:
                note(f"{sname}.{name}: no C_ASSERT(FIELD_OFFSET) in driver")
            elif declared != off:
                fail(f"{sname}.{name}: C_ASSERT offset 0x{declared:X} != layout 0x{off:X}")

    for sname in sorted(set(drv["structs"]) - set(client_structs)):
        note(f"{sname}: driver-internal struct (outside the ABI), not compared")

    # device names: \\.\X == \DosDevices\X
    client_path = getattr(cli, "DEVICE_PATH", "")
    m = re.fullmatch(r"\\\\\.\\(.+)", client_path)
    if not m:
        fail(f"unexpected DEVICE_PATH in client: {client_path!r}")
    else:
        name = m.group(1)
        if drv["symlink"] == f"\\DosDevices\\{name}":
            ok(f"symlink {drv['symlink']} matches {client_path}")
        else:
            fail(f"driver symlink {drv['symlink']!r} != \\DosDevices\\{name}")
        if drv["device"] != f"\\Device\\{name}":
            fail(f"driver device {drv['device']!r} != \\Device\\{name}")

    print("\n[1b] driver: forbidden APIs in source")
    found = [api for api in FORBIDDEN_APIS if api in drv["raw"]]
    if found:
        fail(f"internal APIs in source: {found}")
    else:
        ok("no internal API in the source")

    if not args.skip_binary:
        if binary.is_file():
            check_binary(binary)
            note(f"binary sha256: {sha256(binary)}")
        else:
            fail(f"binary missing: {binary} (pass --skip-binary to bypass)")

    print("\nsummary")
    for n in NOTES:
        print(f"  note: {n}")
    if FAILS:
        print(f"  {len(FAILS)} divergence(s):")
        for f in FAILS:
            print(f"   - {f}")
        return 1
    print("  consistent (no divergence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
