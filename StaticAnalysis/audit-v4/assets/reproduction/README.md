# Reproduction files

`probe_mpk_v4.py` is copied verbatim from `StaticAnalysis/probe_mpk_v4.py`. It tests the candidate MPKINFO row layout, checks candidate ranges against package sidecars, samples selected headers, and writes `audit-v4/mpk-candidate-probe.json`. It is not the script that generated the complete coalesced payload header inventory.

The complete 32-byte header scan, magic classification, and bounded full-payload triage were performed with an inline probe that was not saved as a local script. Accordingly, this folder contains no exact reproduction script for those results; `payload-inventory.json` records the resulting counts, references, and limitations. No reproduction script was run during this correction.

The recorded runtime was Python 3.12 at `C:\Users\luiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. `probe_mpk_v4.py` imports only standard-library modules (`argparse`, `collections`, `hashlib`, `json`, `struct`, `pathlib`). It accepts `--install` and expects `Engine.mpkinfo`, `Resources.mpkinfo`, and MPK sidecars there. Its output path is based on the script's parent directory, so use the original `StaticAnalysis` layout if reproducing that candidate-probe JSON.
