# Python / tools/export_current_status.py / Python 3.12+ x64 / installed Blood Strike PE and V7 evidence
"""Export existing static layouts; distinguish them from a live memory dump."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ExternalCore.build import verify_sample


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def constants(path):
    found = {}
    for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                found[target.id] = {"value": value, "line": node.lineno}
                if type(value) is int:
                    found[target.id]["hex"] = hex(value)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path(
        r"E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/status-20261101")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # The repository verifier rechecks original PE/resource bytes and manifests.
    spec = importlib.util.spec_from_file_location("status_delivery", ROOT /
        "StaticAnalysis/integration-evidence/runtime-v7/verify_delivery.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    verifier.OUTPUT = out / "delivery-verification.json"
    if args.sample.resolve() != Path(
        r"E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe").resolve():
        raise ValueError("the V7 resource verifier is pinned to the original installation")
    verifier.main()
    sample = verify_sample(args.sample)
    pe = args.sample.read_bytes()
    nt = struct.unpack_from("<I", pe, 0x3c)[0]
    machine, count, timestamp = struct.unpack_from("<HHI", pe, nt + 4)
    optional_size = struct.unpack_from("<H", pe, nt + 20)[0]
    preferred_base = struct.unpack_from("<Q", pe, nt + 24 + 24)[0]
    sections = []
    for index in range(count):
        off = nt + 24 + optional_size + 40 * index
        name = pe[off:off+8].split(b"\0")[0].decode("ascii", errors="replace")
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from("<4I", pe, off + 8)
        raw = pe[raw_offset:raw_offset+raw_size]
        if len(raw) != raw_size:
            raise ValueError("truncated PE section")
        sections.append(dict(name=name, rva=hex(rva), virtual_size=virtual_size,
            raw_size=raw_size, file_offset=raw_offset, sha256=hashlib.sha256(raw).hexdigest()))
    paths = [ROOT / "ExternalCore" / (name + ".py") for name in (
        "registry", "entity_position", "camera_capture", "render_camera",
        "screenpoint", "python_runtime", "python_owner", "native_properties", "life_state")]
    sources = {str(p.relative_to(ROOT)).replace("\\", "/"):
        dict(sha256=sha(p), constants=constants(p)) for p in paths}
    observation = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
        "@(Get-Process -Name BloodStrike -ErrorAction SilentlyContinue | "
        "Select-Object Id,ProcessName,Path) | ConvertTo-Json -Compress"],
        capture_output=True, text=True, check=True)
    processes = json.loads(observation.stdout) if observation.stdout.strip() else []
    if isinstance(processes, dict):
        processes = [processes]
    contract = ROOT / "StaticAnalysis/integration-evidence/camera-v7/effective-camera-contract.json"
    render = json.loads(contract.read_text(encoding="utf-8"))
    tests = json.loads((out / "tests/summary.json").read_text(encoding="utf-8"))
    for relative, expected in tests["source_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"source changed after current test run: {relative}")
    if tests["status"] != "PASS":
        raise ValueError("current tests did not pass")
    result = dict(format="bloodstrike-static-layout-inventory-v1",
        timestamp_utc=datetime.now(timezone.utc).isoformat(), sample=sample,
        machine=hex(machine), pe_timestamp=timestamp, preferred_image_base=hex(preferred_base),
        scope="existing V7 static layouts rechecked against installed bytes; not newly derived live offsets",
        runtime_dump_created=False, gameplay_validated=False, observed_processes=processes,
        address_rules=dict(rva="actual loaded module base + RVA; preferred base is not a live base",
            field="add field displacement to a validated instance/subobject",
            constants="source constants also include masks, sizes, sentinels and limits; not all are offsets"),
        sections=sections, sources=sources, render_input_contract=render,
        render_contract_sha256=sha(contract), tests=dict(status=tests["status"],
            run=tests["tests_run"], failures=tests["failures"], errors=tests["errors"], skipped=tests["skipped"]),
        unresolved=["live entity/type/dispatch and object lifetime validation",
            "final viewport projection, jitter, scaling and screen pixel equivalence",
            "visibility and input calibration in the game",
            "HP/faction/combat_state use effective attributes and dynamic metadata, not universal fixed field offsets",
            "watch loop does not dispatch aim input"])
    (out / "static-offsets.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    (out / "STATUS.md").write_text(
        "# Situação verificada — 01/11/2026\n\n"
        "A implementação V7 passa nos 133 testes locais, incluindo nove integrações nativas próprias. "
        "Isso não demonstra funcionamento em partida. O loop watch não envia movimentos de mira; "
        "a projeção final, a visibilidade e a calibração no jogo continuam pendentes.\n\n"
        f"A amostra instalada confere com o SHA-256 `{sample['sha256']}`. "
        "As evidências estáticas, recursos e manifestos V7 foram reconferidos; veja delivery-verification.json.\n\n"
        f"Processos BloodStrike observados: {len(processes)}. Nenhum dump de memória foi produzido. "
        "static-offsets.json consolida constantes existentes com arquivo/linha/hash, seções do PE e o contrato "
        "de câmera. Trata-se de exportação estática da build existente, não de offsets novos obtidos em runtime.\n\n"
        "RVA exige a base efetiva do módulo em execução. Deslocamentos de campos exigem a instância "
        "e o subobjeto corretos. HP/facção/estado usam metadados dinâmicos; não há um deslocamento "
        "fixo universal demonstrado. Os offsets de terceiros continuam sem validação.\n",
        encoding="utf-8")
    print(json.dumps(dict(output=str(out), tests=result["tests"], processes=len(processes),
        runtime_dump_created=False, gameplay_validated=False)))


if __name__ == "__main__":
    main()
