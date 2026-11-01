# Local-player module route, V6

The disk investigation resolves a native root to the interpreter module dictionaries. It does **not** observe a running `gclient.genv` module or its `player` value. All target operations were file reads, SHA-256 checks and disassembly; no target code was loaded or executed and no process was opened.

Pinned executable: `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe`, SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`.

## Exact route

1. Runtime object is at module RVA `0x925f000`, in the native `PyRuntim` PE section. The first bytes spell `xdebugpy`; following uint64 values are version `0x030e00f0` and free-threaded flag `0`.
2. Read the interpreter-list pointer at module RVA `0x925f328`. Each interpreter's next pointer is at `+0x1c68`, and signed 64-bit ID at `+0x1c70`. Main interpreter ID is zero per the matching CPython source; the head itself is the newest interpreter and must not automatically be called main.
3. The interpreter's imports/modules pointer is at `+0x1de8`. Conservatively require an exact pinned `PyDict_Type` before using the existing dictionary reader.
4. Look up the exact Unicode key `gclient.genv` in that dictionary. Require module-object `ob_type` at `+0x08` to equal module base plus `0x7a1b1f0` (exact `PyModule_Type`). Its native type name is `module`, and `tp_basicsize` is `0x38`.
5. Read the module dictionary pointer at module object `+0x10`. Require an exact `PyDict_Type`, then look up `player` / `main_player` according to the previously established model assignments and lifetime.

The machine-readable route is `local-player-route.json`. Dictionary and Unicode formats remain the contracts in `../python-owner-v5/layout-contract.json`; the host Python version is unrelated to target object layout.

## Native corroboration

These offsets are not calculated from an assumed compiler layout. `_PyRuntime` contains a self-describing CPython debug-offset table. Its fields are labeled by the matching `v3.14.0/Include/internal/pycore_debug_offsets.h`; bytes and table addresses are retained in `head-and-module.json`. Runtime head (`0x328`), interpreter next (`0x1c68`), interpreter ID (`0x1c70`), and interpreter modules (`0x1de8`) are literal uint64 values in that native table.

- `runtime-root.json`: instruction RVA `0x2af9e7f` passes address `0x925f000` to runtime initialization function `0x2addac0`. That function initializes the runtime and writes the same debug cookie. This independently ties the data section to runtime use.
- `head-and-module.json`: function RVA `0x2adc8e0` loads the head from `0x925f328`, compares IDs at `+0x1c70`, and follows `+0x1c68`.
- `runtime-follow.json`: function RVA `0x2abe0d0` obtains interpreter through thread state `+0x10` and its modules through `+0x1de8`; its null error references native `sys.modules` text. Function `0x2abdb90` independently repeats this chain.
- `head-and-module.json`: function RVA `0x2a94850` verifies module type `0x7a1b1f0`, then returns object `+0x10`. Its behavior matches `PyModule_GetDict` in `Objects/moduleobject.c` (line 560); native type bytes and string are recorded in `local-player-route.json`.

Every disassembled instruction record retains RVA, preferred VA, file offset, exact bytes, text, and RIP/direct-branch targets where relevant. The function naming is source-correlated inference; actual instruction and data addresses are observed disk facts. All six queried C API/data names are absent from the 651-name PE export table, so exported-name lookup is not required for this route.

## Boundaries and remaining questions

The runtime interpreter-head slot is zero in the disk image. Actual interpreter, dictionary, module and player pointers are initialized at runtime; this investigation cannot retrieve those values from the PE. It establishes where to acquire them in an authorized recording or future observation, not their current presence.

A reader should bound list traversal, reject cycles and invalid pointers, preserve interpreter identity, reject ambiguous module matches, and recheck the entire chain. Native code protects interpreter iteration with a mutex that an external reader cannot acquire through read-only access. Repeated equal observations do not prove lifetime, atomicity, or absence of ABA. Modules and player attributes may disappear during startup, teardown, or owner destruction; `sys.modules` can also be replaced by a non-dict mapping, which a conservative decoder should reject.

This route does not establish which gameplay class is an opponent, connect a particular observed player to a native actor, or validate viewport equivalence. It also does not prove the module is registered specifically under `gclient.genv`; that exact runtime key must be checked instead of assuming that a packaged script filename guarantees registration.

## Reproduction

Run scripts `01-runtime-seeds.py` through `05-contract.py` in order with the supplied Python runtime. They reuse the workspace's read-only `RawPE` / iced-x86 tooling, check the pinned SHA-256, and do not import the target into a new disassembler database. No MCP REA tools were exposed in this agent session; the existing raw-PE evidence workflow was used instead. `source-manifest.json` records official CPython v3.14.0 sources and their downloaded SHA-256 values. The CPython license is copied beside these source artifacts.
