# Python | ExternalCore/snapshot.py | Python 3.12+ | versioned recorded-memory input/output.
from dataclasses import asdict, is_dataclass
import json
import math
from pathlib import Path

from .build import ModuleIdentity
from .memory import Segment, SnapshotMemory

FORMAT = "bloodstrike-external-memory-v1"
MAX_FILE = 32 * 1024 * 1024


def load_snapshot(path):
    with Path(path).open("rb") as source:
        raw = source.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError("snapshot exceeds 32 MiB file budget")
    obj = json.loads(raw)
    if obj.get("format") != FORMAT:
        raise ValueError("unsupported snapshot format")
    module = ModuleIdentity(**obj["module"])
    if not isinstance(obj.get("provenance"), str) or not obj["provenance"]:
        raise ValueError("snapshot provenance must be declared")
    segments = obj["segments"]
    if not isinstance(segments, list) or len(segments) > 100000:
        raise ValueError("invalid or excessive segment count")
    memory = SnapshotMemory(Segment(item["address"], bytes.fromhex(item["hex"])) for item in segments)
    return memory, module, obj["provenance"]


def json_value(value):
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("+Infinity" if value > 0 else "-Infinity")
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")
