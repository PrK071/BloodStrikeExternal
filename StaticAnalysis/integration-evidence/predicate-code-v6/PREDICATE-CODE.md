# Predicate code identity, V6

The pinned PE supports a passive, typed route from a Python function object to its current adaptive code bytes. A runtime function name or class name alone does not prove that the active method implements the packaged predicate. This evidence records layouts, native corroboration, and a canonical baseline for `IGameLogicBase.IsEnemy`; it does not observe or execute a live predicate.

Target SHA-256: `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. All addresses below are RVAs unless a structure-relative offset is explicitly indicated.

## Object contract

| Object | Required native type RVA | Field | Offset |
|---|---:|---|---:|
| PyFunctionObject | `0x7a135a0` | func_code | `0x30` |
| PyFunctionObject | same | func_name / func_qualname | `0x20` / `0x28` |
| PyFunctionObject | same | func_module | `0x68` |
| PyFunctionObject | same | defaults / kwdefaults / closure | `0x38` / `0x40` / `0x48` |
| PyCodeObject | `0x7a28410` | signed ob_size, in code units | `0x10` |
| PyCodeObject | same | co_consts / co_names | `0x18` / `0x20` |
| PyCodeObject | same | co_name / co_qualname | `0x78` / `0x80` |
| PyCodeObject | same | co_code_adaptive | `0xd0` |

`ob_type` is at `+0x08`. Exact native function type has `tp_basicsize=0x98`, itemsize zero. Exact code type has `tp_basicsize=0xd0`, itemsize two; the complete C struct with its single char placeholder occupies `0xd8` bytes after alignment. Do not confuse `sizeof(PyCodeObject)` with the adaptive code start or type allocation basicsize. Byte length is `2 * Py_SIZE(code)`, with a signed bounded size checked before multiplication/read. This is a GIL build (`free_threaded=0` in the previously recovered native runtime table); no thread-local bytecode layout is assumed.

`predicate-code-contract.json` contains further source-derived fields and explicitly separates individually corroborated offsets from remaining ABI-derived fields.

## Native proof

- `native-types-and-members.json` records type names, type header values, and member/getset descriptors. Function `__module__` has descriptor RVA `0x7a13028` and offset `0x68`. Code `co_consts`, `co_names`, `co_name`, `co_qualname` descriptors are at `0x7a28080`, `0x7a280a8`, `0x7a280f8`, `0x7a28120`.
- `native-getters.json`: the function `__code__` getter at `0x2a19c60` loads `+0x30`; its setter at `0x2a19cb0` checks the incoming exact native code type. Name and qualname getters `0x2a19e70` / `0x2a19f10` load `+0x20` / `+0x28`.
- The native `xdebugpy` self-describing offset table places `co_code_adaptive` at `0xd0`. It also reports struct size `0xd8`, names, and other code fields; these values are retained separately in `native-getters.json`.
- Code `co_code` getset at `0x7a282b8` points to `0x2b23240`, which forwards to `0x2b20c30`. The latter reads code `+0x10`, doubles that size and copies from `+0xd0` (instructions `0x2b20c81`–`0x2b20c99`). It then deoptimizes each instruction and clears its inline cache words for the exposed `co_code` bytes object. It is evidence only; this investigation never calls the getter.
- Both full 256-byte source-generated maps occur exactly once in the PE: `_PyOpcode_Caches` at `0x59bde60`, `_PyOpcode_Deopt` at `0x59bdf60`. `opcode-tables.json` records their complete bytes, values and file offsets.
- Native base-code-unit helper `0x2babf10` loads the word from `code+0xd0+index*2`. Its ordinary path replaces the low opcode byte through `_PyOpcode_Deopt` while preserving the high argument byte; additional paths handle executors/monitoring. Our conservative contract rejects those additional cases.

Every instruction evidence row includes exact bytes, file offset, RVA and decoded text. `native-code-bytes.json` uses explicitly bounded contiguous ranges to include compiler-separated exception-directory fragments; it is not a claim that arbitrary neighboring functions are part of a single body.

## Baseline identity and normalization

The baseline is MPK index `108818`, code filename `gshare/game_logic/igame_logic_base.py`, qualified name `IGameLogicBase.IsEnemy`. The checked decoded stream SHA-256 is `c69a1b41935d7a6f56bc7c43be13665325816d9ff5191624f963ee12a5c98af9`. Its 174 bytes (87 code units) have SHA-256 `9cfb18d4557dce7c882bfc8df9a3ce7368b1e8a97abf786a0c15d59bf0b30219`.

Canonical identity serializes 37 triples `[byte_offset, base_opcode, combined_argument]` as compact JSON with no final newline. SHA-256: `b632457e07b643ddb05ff3b4de958097174ce648941cd15075b3b9f6831f20c5`. `baseline-is-enemy.json` contains the triples, original code bytes, source hashes, and required semantic fields.

Walk words from offset zero. Reject unsupported opcodes before mapping; map each ordinary opcode using Deopt, assemble any EXTENDED_ARG bytes, emit the triple, then skip exactly Caches[base] words. Inline cache payloads are runtime data and must not be decoded as opcodes. Reject top-level CACHE, unknown opcodes, every opcode at or above `MIN_INSTRUMENTED_OPCODE=234`, ENTER_EXECUTOR=255, truncated caches, odd lengths, more than three EXTENDED_ARG prefixes, and dangling prefixes. The native ordinary deopt path confirms that ordinary specialization preserves the argument byte. No instrumentation/executor reconstruction is attempted.

The fingerprint script parsed the checked MPK stream to EOF without evaluating its code. A synthetic copy substitutes an available specialization at each eligible instruction (13 instructions), fills cache payloads with nonzero bytes, and confirms that the canonical result remains identical. Separate synthetic CACHE/instrumentation/executor cases are rejected. These are parser checks, not observations of game specialization.

## Identity limits

The opcode fingerprint is only one required condition. Compare the complete semantic inputs too: `co_names=('faction',)`, exact bool constants `(False, True)`, argument counts `3/0/0`, locals `('self','a','b')`, flags, stack size, locals kinds, exception table, and absence of unsupported closure/default bindings. Otherwise a function with the same opcodes and labels can refer to different attributes or constants. Mutable name/qualname/module labels are context rather than proof.

The current method still must be resolved from the actual active game-logic instance, including instance dictionary, type/MRO dictionary and descriptor precedence. Reject unresolved custom dispatch instead of inferring the active implementation from a class name. Even the verified body depends on operand truthiness, `faction` access, and comparison behavior; custom descriptors or operand types may change those operations. Code identity does not prove category semantics for arbitrary objects.

A passive snapshot must bracket/recheck the function pointer, code pointer, size, bytes and semantic fields. Equal reads cannot prove atomicity, object lifetime or absence of ABA. No protected process was opened, no input was sent, no target Python/native code executed, and no core/test files or earlier evidence directories were modified.

## Reproduction

Run `01-types.py` through `06-contract.py` with the supplied Python runtime. The scripts reuse the existing read-only PE parser and iced-x86 decoder, confirm target SHA-256, and parse the selected MPK as data. Official CPython v3.14.0 sources are identified in `source-manifest.json`; their license is included. No new whole-PE disassembler import was performed.
