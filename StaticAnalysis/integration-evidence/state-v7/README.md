# CombatState numeric contract — V7

Static disk-only analysis for BloodStrike.exe SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. It reuses the V6 `SelectTarget`/caller anchors, performs hash-checked literal scanning, and parses only two positive MPK streams. It does not execute target bytecode, import game modules, launch or inspect the game, or edit core/tests.

## Numeric values established from the definition

MPK index `141076` contains `gshare/consts.py` (decoded SHA-256 `3ef7443167b4c9b6e4e5b63a79a1c2fcc83c6b9292cfd6617c9ce633eb5408ac`). Its `CombatState` body at line 282 assigns these values directly with CPython 3.14 `LOAD_SMALL_INT` followed by `STORE_NAME`:

| Member | Value |
| --- | ---: |
| `ALIVE` | 0 |
| `DYING` | 1 |
| `DEAD` | 2 |
| `GHOST` | 3 |
| `NONE` | 4 |
| `SPIRIT` | 5 |

The CPython 3.14 `LOAD_SMALL_INT` opcode pushes a small integer equal to its operand ([official Python 3.14 bytecode notes](https://docs.python.org/3.14/whatsnew/3.14.html#cpython-bytecode-changes)). The module imports `enum` from `gshare.utils`, then constructs `CombatState` with that class as its base. This is the game's custom enum metaclass path, not a stdlib `enum.Enum`/`IntEnum` declaration.

The custom factory is in MPK index `66389`, `gshare/utils.py` (decoded SHA-256 `6d25d8acdae724ffed4e7544a4eaed6668a9c1a45efc5ee2898c8d9462882cea`). `EnumMetaclass.__new__` iterates the class namespace, builds `value_to_names` and `name_to_values`, and calls `type.__new__(mcs, clsname, bases, bdict)` with the original class namespace. It adds those two maps and does not rewrite the `ALIVE`/`DYING` assignments, so their class attributes remain integer 0 and 1. The full function code hash and relevant opcode operands are retained in `04-combatstate-numeric-contract.json`.

## State filter contract from the consumer

The existing V6 proof for MPK index `68262`, `gclient/framework/util/assist_aim_util.py`, shows `AssistAim.SelectTarget` has code-byte SHA-256 `a06f588dcb9ec7072759f71dd612025ffc65a6a8e6253ff2fbd9291890c457bf`, `argcount=5`, and positional arguments `self, max_dist, detect_box, randomOne, combat_states`. Its default is exactly `(CombatState.ALIVE,)`, now grounded numerically as `(0,)`.

The Juren Fly Slash caller explicitly supplies `(CombatState.ALIVE, CombatState.DYING)`, numerically `(0, 1)`. The original candidate filter is therefore:

- Base `SelectTarget` default: accept `combat_state == 0`.
- Juren Fly Slash override: accept `combat_state == 0` or `combat_state == 1`.
- Do not label state `1` as generally alive; it is admitted only by that caller-specific tuple.

For a runtime cross-check without hardcoded default assumptions, inspect the loaded `AssistAim.SelectTarget` only if its code fingerprint and argument layout match. Read its `__globals__["CombatState"]`, verify class namespace values `ALIVE==0` and `DYING==1`, and confirm `__defaults__[-1][0]` equals that class's `ALIVE`. For the Juren path, its explicit caller tuple supplies the second allowed member. This runtime route reads objects; it does not execute the target function.

The native-properties V6 audit separately finds raw numeric property-map support and the `combat_state` property name, but its PE literal search did not find a native symbolic `CombatState`/`ALIVE`/`DYING` binding. The numeric meanings here are established by the pinned Python schema and original Python consumers. The existing attribute-dispatch caveat still applies: an external reader must prove that its value came from the intended `combat_state` property path before applying these meanings.

## Bounded extraction

- `00_scan_combatstate_literals.py` / `00-combatstate-literal-scan.json`: bounded byte-literal scan of MPK payloads with per-entry/aggregate limits and compressed/decoded hash verification; found `gshare/consts.py` at index 141076 and `gshare/utils.py` at index 66389.
- `01_parse_combatstate_module.py` / `01-combatstate-definition.json`: full static parse of only `gshare/consts.py`.
- `02_scan_enum_factory.py` / `02-scan-enum-factory.json` and `03_parse_enum_factory.py` / `03-enum-factory-definition.json`: bounded exact-path search followed by full static parse of only `gshare/utils.py`.
- `04_extract_numeric_state_contract.py` / `04-combatstate-numeric-contract.json`: consolidates the enum values, metaclass construction, V6 consumer fingerprint, and runtime verification route.

The literal scans have explicit limits and skipped/error records. They are not a clean-room extraction of every oversized or malformed resource entry.

