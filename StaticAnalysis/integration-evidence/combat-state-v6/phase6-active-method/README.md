# Active `IsEnemy` method gate — V6 phase 6

Static-only review against pinned target SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. This phase reuses the hash-checked phase 3–5 parser outputs; it does not reparse the corpus, execute MPK bytecode, import the target modules, open the game, or inspect a process.

## What identifies the active object

MPK index `29779`, `gclient/framework/entities/space.py`, establishes the producer path: `Space.init` initializes `self.game_logic` to `None` and publishes `self` as `genv.space`; `Space.enter` stores the entering entity into `self.game_logic` only on the `entity.IsGameLogic` true branch. `PlayerCombatAvatar` ADS consumers (index `107853`) then read `genv.space.game_logic` and call its `IsEnemy`; `AssistAim.SelectTarget` (index `68262`) reaches `owner.game_logic.CanDamage`.

This proves which reference the original consumer uses, but `IsGameLogic` is only an entity marker. It does not identify the method implementation. `Space` derives from native-facing `ClientSpace`/`Entity` and its decorated `SpaceClass` path. The selected `Space`, `ClientSpace`, `CGameLogicBase`, and `IGameLogicBase` Python code objects contain no `__getattr__` or `__getattribute__` methods. That bounded absence does not exclude native lookup hooks/descriptors, decorators, or hooks in unselected bases.

## Function fingerprints and overrides

The general implementation is `IGameLogicBase.IsEnemy` from index `108818`, code-byte SHA-256 `9cfb18d4557dce7c882bfc8df9a3ce7368b1e8a97abf786a0c15d59bf0b30219`. `CGameLogicBase` in index `145546` is built as a subclass of `IGameLogicBase` and does not define its own `IsEnemy`. The `GameLogicBase` entity uses `Components(...)`; mode/component composition can change the class dictionary and therefore the resolved implementation.

Known overrides in the parsed scope:

- `MobaFactionMapInfoMixin.IsEnemy`, index `92227`, code-byte SHA-256 `c3cd9518e161567d17b7fa72914ebffe6e5cf9b45e65e1c0f97590f8d21db33f`.
- `CGameLogicPeekaboo.IsEnemy`, index `132180`, code-byte SHA-256 `23ba15b51dca4b6f9e4999199aa5822e82b7eead2944d94a6961e8ee34473b5a`.
- `GameLogicZombieComp.IsEnemy`, index `80751`, code-byte SHA-256 is recorded in `01-active-method-gate.json`.

These examples are enough to reject a class-name or `IsGameLogic`-only gate. The set is not asserted complete across every mode or component in the MPK.

A strict runtime gate must start from the actual active object and resolve `IsEnemy` using instance and type/MRO lookup, including component-injected methods. It can accept only a verified, mode-approved function fingerprint and must reject unknown wrappers, per-instance overrides, and unresolved native descriptors. For the base predicate, compare the resolved function/code object to the `IGameLogicBase.IsEnemy` fingerprint above. The static evidence cannot determine which method wins for the live instance.

## `AssistAim.SelectTarget` state anchor

The full code-byte fingerprint for `AssistAim.SelectTarget` is `a06f588dcb9ec7072759f71dd612025ffc65a6a8e6253ff2fbd9291890c457bf` (module index `68262`, decoded module SHA-256 `8163bc535975fd931d2df900fc04bf0d0402e1e5555aa6c2c3d2ffd53168f3de`). Its class-body bytecode builds the default tuple `(CombatState.ALIVE,)` and installs it on the function as its positional defaults. The runtime semantic anchor is `AssistAim.__dict__["SelectTarget"].__defaults__[-1][0]`: the enum member object itself. The module imports `CombatState` from `gshare.consts`; neither its integer encoding nor its concrete runtime type is inferred here.

## Machine evidence

`01_extract_active_method_gate.py` regenerates `01-active-method-gate.json` from the hash-checked phase 3, phase 4, and phase 5 reports. It records module/code hashes, the general implementation, known parsed overrides, selected attribute-hook audit, active-reference producer, and `SelectTarget` function/default fingerprints.
