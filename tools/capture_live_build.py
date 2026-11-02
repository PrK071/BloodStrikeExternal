# Python / tools/capture_live_build.py / Python 3.12+ x64 Windows / explicitly selected Blood Strike process
"""Read a build-bound mapped image and collect live roots/pipeline observations."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import struct
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ExternalCore.build import ModuleIdentity, verify_sample
from ExternalCore.snapshot import write_json
from ExternalCore.win32_memory import WindowsProcessMemory, find_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        raise FileExistsError("select a new output directory; prior evidence is preserved")
    out.mkdir(parents=True)
    result = dict(status="RUNNING", pid=args.pid,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        memory_write_performed=False, target_code_called=False,
        input_dispatched=False, gameplay_validated=False)
    status = out / "capture-status.json"
    write_json(status, result)
    try:
        sample = verify_sample(args.sample)
        result["sample"] = sample
        with WindowsProcessMemory(args.pid) as reader:
            if os.path.normcase(os.path.realpath(reader.image_path)) != os.path.normcase(sample["path"]):
                raise ValueError("selected process path does not match verified sample")
            selected = find_module(args.pid, sample["path"])
            if selected.size != sample["image_size"]:
                raise ValueError("mapped module size differs from sample")
            module = ModuleIdentity(selected.base, selected.size, sample["sha256"])
            result["module"] = dict(base=hex(module.base), size=module.size,
                sha256_of_disk_sample=module.sha256)
            if reader.read(module.base, 2) != b"MZ":
                raise ValueError("live module header is not MZ")
            result["memory_read_performed"] = True
            roots = {}
            for name, rva in (("actor_registry", 0x8B7CD90), ("engine_root", 0x80D5980),
                              ("render_state", 0x80F3840), ("interpreter_head", 0x925F328)):
                try:
                    raw = reader.read(module.address(rva, 8), 8)
                    roots[name] = dict(rva=hex(rva), address=hex(module.base+rva),
                        pointer=hex(struct.unpack("<Q", raw)[0]), raw_hex=raw.hex(),
                        meaning="observed bytes at static RVA; pointee semantics require downstream validation")
                except OSError as exc:
                    roots[name] = dict(rva=hex(rva), error=str(exc))
            write_json(out / "live-roots.json", roots)
            result["roots"] = roots
            # Raw virtual-layout image: offset N means module_base+N, not a PE raw offset.
            spans, holes = [], []
            dump = out / "BloodStrike.mapped-image.bin"
            with dump.open("xb") as stream:
                stream.truncate(module.size)
                for offset in range(0, module.size, 0x10000):
                    length = min(0x10000, module.size-offset)
                    try:
                        raw = reader.read(module.base+offset, length)
                    except OSError:
                        for page in range(offset, offset+length, 0x1000):
                            size = min(0x1000, module.size-page)
                            try:
                                raw = reader.read(module.base+page, size)
                            except OSError as exc:
                                holes.append(dict(rva=hex(page), size=size, error=str(exc)))
                            else:
                                stream.seek(page); stream.write(raw)
                                spans.append(dict(rva=hex(page), size=size,
                                    sha256=hashlib.sha256(raw).hexdigest()))
                    else:
                        stream.seek(offset); stream.write(raw)
                        spans.append(dict(rva=hex(offset), size=length,
                            sha256=hashlib.sha256(raw).hexdigest()))
            with dump.open("rb") as stream:
                dump_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            image_report = dict(format="mapped-image-read-v1", base=hex(module.base),
                image_size=module.size, file=dump.name, sha256=dump_hash,
                complete=not holes, readable_bytes=sum(span["size"] for span in spans),
                spans=spans, holes=holes,
                limitations=["non-atomic sequential observation; target continued running",
                    "unreadable ranges are zero-filled placeholders, not observed zeros",
                    "virtual image layout, not a reconstructed runnable PE or full process/heap dump"])
            write_json(out / "mapped-image-manifest.json", image_report)
            result["mapped_image"] = {key: image_report[key] for key in
                ("file", "sha256", "complete", "readable_bytes", "image_size")}
            from ExternalCore.pipeline import process_frame
            try:
                frame = process_frame(reader, module, require_render_input=True)
                write_json(out / "live-frame.json", frame)
                result["pipeline"] = dict(status="CAPTURED", actors=len(frame.scene.actors),
                    rejected=len(frame.scene.rejected), aim_reason=frame.aim.reason,
                    final_viewport_validated=frame.scene.final_viewport_validated)
            except (OSError, ValueError, TypeError, RuntimeError) as exc:
                result["pipeline"] = dict(status="UNRESOLVED", error_type=type(exc).__name__, error=str(exc))
            result["status"] = "CAPTURED" if not holes else "PARTIAL_IMAGE_CAPTURE"
    except Exception as exc:
        result.update(status="ERROR", error_type=type(exc).__name__, error=str(exc),
            winerror=getattr(exc, "winerror", None), traceback=traceback.format_exc())
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(status, result)
    return 1 if result["status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
