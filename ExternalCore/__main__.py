# Python | ExternalCore/__main__.py | Python 3.12+ | build-bound collector CLI.
"""Snapshot is offline. Capture requires an explicit PID and original PE path."""
import argparse
import os
from pathlib import Path
import sys

from .build import ModuleIdentity, verify_sample
from .registry import collect_registry
from .snapshot import load_snapshot, write_json


def _guard_output_paths(args):
    inputs = [path for path in (getattr(args, "input", None), getattr(args, "sample", None)) if path]
    outputs = [path for path in (args.output, getattr(args, "svg", None)) if path]
    def same(left, right):
        if os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve())):
            return True
        return left.exists() and right.exists() and os.path.samefile(left, right)
    if any(same(source, target) for source in inputs for target in outputs):
        raise ValueError("output must not overwrite an input or original sample")
    if len(outputs) == 2 and same(*outputs):
        raise ValueError("JSON and SVG outputs must use different files")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build-bound registry, typed camera, ESP and aim-planning pipeline.")
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="decode recorded memory; never opens a process")
    snapshot.add_argument("input", type=Path)
    capture = commands.add_parser("capture", help="explicit read-only Win32 acquisition; no automatic PID selection")
    capture.add_argument("--pid", type=int, required=True)
    capture.add_argument("--sample", type=Path, required=True)
    scene = commands.add_parser("scene", help="offline typed camera/registry -> projection -> ESP/aim planning")
    scene.add_argument("input", type=Path)
    scene.add_argument("--svg", type=Path)
    scene.add_argument("--require-render-input",action="store_true")
    predicate = commands.add_parser("predicate", help="offline function/code identity check; no target calls")
    predicate.add_argument("input", type=Path)
    predicate.add_argument("--function", type=lambda text: int(text,0), required=True)
    predicate.add_argument("--output", type=Path, required=True)
    watch = commands.add_parser("watch", help="explicit PID/window read-only observation loop; no input dispatch")
    watch.add_argument("--pid", type=int, required=True)
    watch.add_argument("--sample", type=Path, required=True)
    watch.add_argument("--hwnd", type=lambda text: int(text, 0), required=True)
    watch.add_argument("--seconds", type=float, default=10)
    watch.add_argument("--fps", type=float, default=30)
    watch.add_argument("--show-overlay", action="store_true")
    watch.add_argument("--output", type=Path, required=True)
    for command in (snapshot, capture, scene):
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--max-nodes", type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        _guard_output_paths(args)
    except (OSError, ValueError) as exc:
        # Do not write an error report over the very input being protected.
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    try:
        if args.command == "predicate":
            from .predicate import inspect_base_is_enemy
            reader, identity, provenance = load_snapshot(args.input)
            proof = inspect_base_is_enemy(reader,identity,args.function)
            write_json(args.output,{"format":"bloodstrike-predicate-body-v1","source":"recorded_memory",
                "provenance":provenance,"module":identity,"body":proof,
                "gameplay_validated":False,"target_code_executed":False})
            print(f"base IsEnemy body matched; dispatch and operand semantics unresolved; {args.output}")
            return 0
        if args.command == "watch":
            from .live import watch as observe
            count = observe(args.pid, args.sample, args.hwnd, args.output, seconds=args.seconds,
                            fps=args.fps, show=args.show_overlay)
            print(f"{count} observation frame(s); {args.output}")
            return 0
        if args.command == "scene":
            from .pipeline import process_frame
            from .render import save_svg
            reader, identity, provenance = load_snapshot(args.input)
            frame = process_frame(reader, identity, max_nodes=args.max_nodes,
                                  require_render_input=args.require_render_input)
            if args.svg:
                save_svg(args.svg, frame.scene.width, frame.scene.height, frame.commands,
                         provenance=provenance)
            write_json(args.output, {"format": "bloodstrike-pipeline-frame-v1", "source": "recorded_memory",
                       "provenance": provenance, "module": identity, "frame": frame,
                       "gameplay_validated": False, "input_dispatched": False})
            print(f"{len(frame.scene.actors)} projected record(s); {args.output}")
            return 0
        if args.command == "snapshot":
            reader, identity, provenance = load_snapshot(args.input)
            frame = collect_registry(reader, identity, max_nodes=args.max_nodes)
            source = {"kind": "recorded_memory", "provenance": provenance,
                      "identity_claim": "snapshot_declared_not_a_live_game_validation"}
        else:
            from .win32_memory import WindowsProcessMemory, find_module
            sample = verify_sample(args.sample)  # Must run before opening a process.
            with WindowsProcessMemory(args.pid) as reader:
                if os.path.normcase(os.path.realpath(reader.image_path)) != os.path.normcase(sample["path"]):
                    raise ValueError("selected PID does not use the verified executable path")
                module = find_module(args.pid, sample["path"])
                if module.size != sample["image_size"]:
                    raise ValueError("mapped module size differs from the verified PE")
                identity = ModuleIdentity(module.base, module.size, sample["sha256"])
                frame = collect_registry(reader, identity, max_nodes=args.max_nodes)
            source = {"kind": "win32_read_only", "pid": args.pid, "path": sample["path"],
                      "identity_claim": "disk_hash_and_module_path_size_not_full_live_image_hash"}
        write_json(args.output, {"format": "bloodstrike-registry-frame-v1", "source": source,
                                 "module": identity, "frame": frame,
                                 "gameplay_validated": False})
        print(f"{len(frame.records)} registry record(s); {args.output}")
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        # Failure must not retain a previous output that could be mistaken for this run.
        write_json(args.output, {"format": "bloodstrike-registry-error-v1", "status": "error",
                                 "error_type": type(exc).__name__, "error": str(exc)})
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
