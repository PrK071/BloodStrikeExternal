# Python | inspect_build.py | Python 3.12+ | Windows x64; inspect local PE files and process access.
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import mmap
from pathlib import Path
import re
import struct


class PortableExecutable:
    def __init__(self, data):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("Missing DOS header")
        pe = self.read("<I", 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise ValueError("Missing PE signature")
        machine, count, stamp, _, _, optional_size, _ = self.read("<HHIIIHH", pe + 4)
        optional = pe + 24
        if self.read("<H", optional)[0] != 0x20B or machine != 0x8664:
            raise ValueError("Expected an AMD64 PE32+ image")
        if count > 96 or optional_size < 112:
            raise ValueError("Invalid PE header sizes")
        self.machine = machine
        self.timestamp = stamp
        self.image_base = self.read("<Q", optional + 24)[0]
        self.image_size = self.read("<I", optional + 56)[0]
        self.header_size = self.read("<I", optional + 60)[0]
        self.entry_point = self.read("<I", optional + 16)[0]
        directories = min(self.read("<I", optional + 108)[0], 16, (optional_size - 112) // 8)
        self.directories = [self.read("<II", optional + 112 + i * 8) for i in range(directories)]
        self.sections = []
        for i in range(count):
            offset = optional + optional_size + i * 40
            name, virtual_size, rva, raw_size, raw_offset = self.read("<8sIIII", offset)
            if raw_size and raw_offset + raw_size > len(data):
                raise ValueError("Section exceeds file bounds")
            self.sections.append({
                "name": name.rstrip(b"\0").decode("ascii", "replace"),
                "rva": rva, "virtual_size": virtual_size,
                "raw_size": raw_size, "raw_offset": raw_offset,
            })

    def read(self, fmt, offset):
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(self.data):
            raise ValueError("PE read exceeds file bounds")
        return struct.unpack_from(fmt, self.data, offset)

    def section(self, rva):
        return next((s for s in self.sections if s["rva"] <= rva < s["rva"] + max(s["virtual_size"], s["raw_size"])), None)

    def rva_to_offset(self, rva):
        if 0 <= rva < min(self.header_size, len(self.data)):
            return rva
        section = self.section(rva)
        if section:
            delta = rva - section["rva"]
            if delta < section["raw_size"]:
                return section["raw_offset"] + delta
        return None

    def offset_to_rva(self, offset):
        for section in self.sections:
            if section["raw_offset"] <= offset < section["raw_offset"] + section["raw_size"]:
                return section["rva"] + offset - section["raw_offset"]
        return offset if 0 <= offset < self.header_size else None

    def cstring(self, offset):
        end = self.data.find(b"\0", offset, min(offset + 1024, len(self.data)))
        if end < 0:
            raise ValueError("Unterminated PE string")
        return self.data[offset:end].decode("ascii", "replace")

    def imported_modules(self):
        if len(self.directories) < 2 or not self.directories[1][0]:
            return []
        rva, size = self.directories[1]
        result = []
        for i in range(min(size // 20, 4096)):
            descriptor = self.rva_to_offset(rva + i * 20)
            if descriptor is None:
                raise ValueError("Import directory is not file-backed")
            fields = self.read("<IIIII", descriptor)
            if not any(fields):
                break
            name = self.rva_to_offset(fields[3])
            if name is None:
                raise ValueError("Import name is not file-backed")
            result.append(self.cstring(name))
        return result

    def anchors(self):
        result = {}
        names = ("GetAllActors", "NewSpike", "Messiah", "FpsPlacer", "ALSTpsPlacer", "GetShootDir", "BaseNetworkable", "TOD_Sky", "il2cpp")
        for name in names:
            marker = name.encode("ascii")
            hits, position, total = [], 0, 0
            while True:
                offset = self.data.find(marker, position)
                if offset < 0:
                    break
                total += 1
                if len(hits) < 8:
                    rva = self.offset_to_rva(offset)
                    hits.append({"file_offset": hex(offset), "rva": hex(rva) if rva is not None else None})
                position = offset + len(marker)
            result[name] = {"occurrences": total, "first_locations": hits}
        return result


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def process_access(pid):
    if not hasattr(ctypes, "WinDLL"):
        return {"available": False, "reason": "Windows API required"}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.OpenProcessToken.restype = wintypes.BOOL
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.GetTokenInformation.restype = wintypes.BOOL

    def describe(handle):
        result = {}
        buffer = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(buffer))
        if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
            result["image_path"] = buffer.value
        else:
            result["image_path_error"] = ctypes.get_last_error()
        token = wintypes.HANDLE()
        if security.OpenProcessToken(handle, 0x8, ctypes.byref(token)):
            try:
                elevated, size = wintypes.DWORD(), wintypes.DWORD()
                if security.GetTokenInformation(token, 20, ctypes.byref(elevated), ctypes.sizeof(elevated), ctypes.byref(size)):
                    result["elevated"] = bool(elevated.value)
                else:
                    result["token_information_error"] = ctypes.get_last_error()
            finally:
                kernel.CloseHandle(token)
        else:
            result["token_open_error"] = ctypes.get_last_error()
        return result

    result = {"pid": pid, "inspector": describe(kernel.GetCurrentProcess())}
    query = kernel.OpenProcess(0x1000, False, pid)
    if query:
        try:
            result["target"] = describe(query)
        finally:
            kernel.CloseHandle(query)
    else:
        result["query_error"] = ctypes.get_last_error()
    read_handle = kernel.OpenProcess(0x1010, False, pid)
    result["vm_read_handle_opened"] = bool(read_handle)
    result["vm_read_open_error"] = 0 if read_handle else ctypes.get_last_error()
    if read_handle:
        kernel.CloseHandle(read_handle)
    result["memory_read_performed"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description="Inspect the installed BloodStrike executable and supplied offset provenance.")
    parser.add_argument("--install", type=Path, required=True)
    parser.add_argument("--offsets", type=Path, required=True)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    install = args.install.resolve(strict=True)
    exe = install / "Engine" / "Binaries" / "Win64" / "BloodStrike.exe"
    manifest = install.parent.parent / "appmanifest_3199170.acf"
    manifest_text = manifest.read_text(encoding="utf-8-sig") if manifest.is_file() else ""
    steam = {}
    for field in ("appid", "name", "buildid", "TargetBuildID"):
        match = re.search(r'"' + field + r'"\s+"([^"\r\n]+)"', manifest_text)
        steam[field] = match.group(1) if match else None
    patch_file = install / "LocalData" / "Patch" / "pkgversion"
    offsets = json.loads(args.offsets.read_text(encoding="utf-8-sig"))
    if not isinstance(offsets.get("offsets"), dict):
        raise ValueError("offsets must be an object")
    parsed = {}
    for name, value in offsets["offsets"].items():
        if not isinstance(value, str) or not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|[0-9]+)", value):
            raise ValueError("Invalid numeric offset: " + name)
        parsed[name] = int(value, 16 if value.lower().startswith("0x") else 10)
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "steam": steam,
              "patch_pkgversion": patch_file.read_text(encoding="utf-8-sig").strip() if patch_file.is_file() else None,
              "executable": {"path": str(exe), "file_size": exe.stat().st_size, "sha256": fingerprint(exe)},
              "supplied_offsets": {"path": str(args.offsets.resolve()), "sha256": fingerprint(args.offsets),
                                   "count": len(parsed), "declared_version": offsets.get("version"),
                                   "declared_updated_at": offsets.get("updated_at"),
                                   "zero_values": [key for key, value in parsed.items() if value == 0]}}
    with exe.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        pe = PortableExecutable(image)
        report["pe"] = {"machine": hex(pe.machine), "preferred_image_base": hex(pe.image_base),
                        "size_of_image": hex(pe.image_size), "entry_point_rva": hex(pe.entry_point),
                        "sections": pe.sections, "imports": pe.imported_modules(), "anchors": pe.anchors()}
        report["supplied_offsets"]["large_values_as_executable_rvas"] = [
            {"name": key, "value": hex(value), "inside_image": value < pe.image_size,
             "section": pe.section(value)["name"] if pe.section(value) else None}
            for key, value in parsed.items() if value > 0x100000]
        report["reference_page_candidate"] = {
            "source": "https://globality.live/case-bloodstrike", "claimed_actor_manager_rva": "0x8a8e810",
            "section": pe.section(0x8A8E810)["name"] if pe.section(0x8A8E810) else None,
            "file_backed": pe.rva_to_offset(0x8A8E810) is not None,
            "semantic_validation": "NOT_VALIDATED; section membership alone does not identify an actor manager"}
    if args.pid is not None:
        report["process_access"] = process_access(args.pid)
    report["feature_status"] = {name: "NOT_IMPLEMENTED_OR_VALIDATED" for name in ("esp", "aimbot", "radar", "no_recoil")}
    report["interpretation_limits"] = [
        "Steam depot build and local patch version are separate identifiers.",
        "Original offsets do not identify a base module; RVA checks here apply only to BloodStrike.exe.",
        "An offset of zero is not intrinsically invalid and is not substituted with a guessed value.",
        "String presence is static evidence, not proof of a live object layout.",
        "Failure to open VM_READ can reflect token integrity or access controls; the probe does not establish which protection caused it.",
        "An opened VM_READ handle would not prove that any candidate offset is correct.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_name(args.out.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(json.dumps({"report": str(args.out.resolve()), "build": steam.get("buildid"), "patch": report["patch_pkgversion"],
                      "image_size": report["pe"]["size_of_image"], "process_access": report.get("process_access")}, ensure_ascii=True))


if __name__ == "__main__":
    main()
