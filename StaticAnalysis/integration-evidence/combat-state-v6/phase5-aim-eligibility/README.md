# Aim target state eligibility — V6 phase 5

Static-only MPK evidence tied to executable SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. No process access, target execution, bytecode execution, runtime imports, or payload evaluation. The parser verifies compressed/decoded MPK hashes and parses the selected modules through EOF.

## Exact `AssistAim.SelectTarget` state contract

MPK index `68262`, `gclient/framework/util/assist_aim_util.py`, decoded SHA-256 `8163bc535975fd931d2df900fc04bf0d0402e1e5555aa6c2c3d2ffd53168f3de`, defines `AssistAim.SelectTarget(self, max_dist, detect_box, randomOne, combat_states)` at line 1198. `AssistAim` class-body bytecode at offsets 130–162 builds the method's default tuple from `CombatState.ALIVE`: `LOAD_NAME CombatState`, `LOAD_ATTR ALIVE`, `BUILD_TUPLE 1` for the one accepted state, `BUILD_TUPLE 1` for the positional-defaults tuple, then `SET_FUNCTION_ATTRIBUTE 1` (defaults). Therefore the default state set is exactly `(CombatState.ALIVE,)`.

The target loop extracts `collision.Body.Parent`, reads its `owner`, keeps combat-avatar targets or the admitted Eva-monster path, applies `IsAssistAimTarget`, calls `player.game_logic.CanDamage(cur_result, player)`, and then reads `cur_result.combat_state`. At offsets 630–664 it tests `cur_result.combat_state not in combat_states`; that branch jumps back to the next collision when true. CPython 3.14 documents `CONTAINS_OP` with invert bit 1 as `not in` ([official `dis` documentation](https://docs.python.org/3.14/library/dis.html#opcode-CONTAINS_OP), [pinned CPython 3.14.0 `Lib/dis.py`](https://github.com/python/cpython/blob/v3.14.0/Lib/dis.py#L3265-L3272)). Thus this is an allow-list: a candidate continues through range/visibility/dot tests only when its `combat_state` belongs to the supplied set.

`AssistAim.TestSelectTarget` calls `self.SelectTarget(self.max_dist, self.detect_box, False)` and omits `combat_states`, so that test path uses the default `(CombatState.ALIVE,)`.

## Caller-specific override: Juren Fly Slash

MPK index `123809`, `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_spell_juren.py`, decoded SHA-256 `da3df22f2c13a3c1cffbfba887b345c983f95e0f2d8d9f3a5c11d1325f5ca8a`, defines `PlayerCombatAvatarMember.StartJurenFlySlashMeleeAssistAim` at line 654. It calls `self.StartAssistAimMelee((consts.CombatState.ALIVE, consts.CombatState.DYING))` (bytecode offsets 586–720). The state tuple is explicit and caller-specific: this Juren fly-slash assistance path permits both ALIVE and DYING. It demonstrates why the default cannot be promoted to a universal rule for every invocation.

The forwarding chain is also explicit:

- `PlayerCombatAvatarMember.StartAssistAimMelee(self, combat_states)` in index `86590`, line 779, exits for the assist-ban reason, missing `genv.player`, Football match type, absent melee assist, or inactive weapon, then forwards the caller's `combat_states` argument to `AssistAimMelee.StartAssistAim`.
- `AssistAimMelee.StartAssistAim(self, combat_states)` in index `68262`, line 1450, forwards it to `_StartAssistAim`.
- `AssistAimMelee._StartAssistAim` at line 1458 calls `self.SelectTarget(self.max_dist, self.detect_box, False, combat_states=...)` and stores the returned target.

The caller-specific tuple is supplied only by the Juren Fly Slash path found in this bounded candidate set. The general entrypoint accepts a caller-provided list, so other invocations must be checked at their own caller before assigning a state allow-list. Mode classes `PlayerCombatAvatarSniperMode.StartAssistAimMelee` (index `9715`, line 56) and `PlayerCombatAvatarArmsRaceMode.StartAssistAimMelee` (index `10842`, line 108) return `None`; they do not supply another state list.

## State transitions and knockdown are distinct

MPK index `14066`, `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_combat_unit.py`, decoded SHA-256 `5a2ccf79f644a908e6475ed76c870312fb61526b260dfc0dc90d0c772c9c648`:

- `CombatAvatarMember._on_set_combat_state` (line 331) compares `combat_state` against `CombatState.DEAD`, `ALIVE`, `DYING`, `GHOST`, and `SPIRIT`; these route to `OnDead`, `OnReborn`, `OnDying`, `OnGhost`, and `OnSpirit` (among other updates). These are event/state handlers, not a general `IsDead` method.
- `CombatAvatarMember.OnDying` (line 526) invokes `model.OnKnockDown(is_dying)` and manipulates the `KNOCK_DOWN` graph-disable reason. This proves a knockdown animation/graph behavior under the DYING handler, but does not establish a separate `CombatState.KNOCKED` enum member.
- `AssistAimTracingTargetNoSearching.IsControllingAdsRotate` and `AssistAimAndShootTracingNoSearching.IsControllingAdsRotate` (index 68262, lines 2717/2849) require the target to be non-null, not destroyed, and `target.combat_state == CombatState.ALIVE` before returning true for their active aim state. This is a separate continuation/control check, not the target-selection caller's full contract.
- `AssistAimMagicBullet.SelectTarget` (same index, line 3186) delegates to `filter_util.IsAimEnemy2D`; its implementation was not present in the selected candidate streams, so no alive/knock rule is inferred for that path.

Both `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_combat_unit.py` (index 14066, module offsets 340–344) and `gclient/framework/util/assist_aim_util.py` (index 68262, offsets 118–122) import `CombatState` by `IMPORT_NAME gshare.consts`, `IMPORT_FROM CombatState`, `STORE_NAME CombatState`. This proves the Python import path `gshare.consts.CombatState`; it does not prove a direct `_gcommon.GameState.CombatState` import or the enum implementation type.

The selected `CombatAvatarMember` class body in index 14066 has no `combat_state` field name or `Property` declaration/default. The property belongs to its native/base contract in the available evidence; no explicit script-side `CombatState.ALIVE` descriptor default is shown.

A passive reader that can inspect the loaded Python module/class object has a source-grounded anchor without hardcoding an integer: `LocalRootModules['gclient.framework.util.assist_aim_util'].AssistAim.__dict__['SelectTarget'].__defaults__[-1][0]` is the actual `CombatState.ALIVE` member object. The class body builds that default at offsets 130–162 and `SET_FUNCTION_ATTRIBUTE 1` installs it as the function defaults. A reader can inspect the object representation/type or compare a field against that member if its conversion is established. The MPK does not establish that the enum is a `PyLong` subclass or reveal its integer value; do not infer zero or substitute a generic integer default.

The symbolic source contracts are therefore exact (ALIVE by default; ALIVE+DYING for the Juren caller), and a runtime enum-object anchor is available through the function defaults. The underlying numeric encoding and native descriptor default remain unknown in this static evidence. No `server_hp > 0` alive rule is supported or used here.

## Machine evidence and bounded scope

- `01_parse_aim_state.py` / `01-aim-state-candidates.json`: full selected code-object records for the aim utility, combat-state callbacks, and state-relationship module, plus three discovered caller modules. Includes full offsets and code hashes.
- `02_bounded_aim_callsite_scan.py` / `02-bounded-aim-callsite-scan.json`: decompressed-string scan with compressed/decoded hash checks over 118 indexed candidates whose paths contain `combat_avatar`, `combatavatarmembers`, or `assist_aim`. It found caller-related positives at indices 9715, 10842, and 123809; only these were added to the full-parser candidate set. This did not reparse the whole MPK corpus.
- `01-aim-state-candidates.json` retains the state bytecode branches and the `AssistAim` class-body `CombatState.ALIVE` default construction. Enum member integers are absent from these records.

## Reader contract

For the base `AssistAim.SelectTarget` default, the original game allows only `combat_state == CombatState.ALIVE`; the Juren fly-slash caller explicitly allows `ALIVE` or `DYING`. A field-only reader can implement that only if it obtains the verified numeric values of the corresponding enum members and knows which caller/mode contract applies. Until then, report the raw `combat_state` or a symbolic `eligible_state` candidate without calling it universally alive/dead. HP is not a substitute for this allow-list.

## Enum source and default-object route

`03-combat-state-enum-default-proof.json` records the `gshare.consts.CombatState` imports, `AssistAim.SelectTarget` defaults construction, and absence of a Python-side `combat_state` descriptor declaration in the selected class body. `03_extract_combat_state_default.py` regenerates that extraction from the hash-checked V6 parser report. The enum object's runtime integer/type remains unknown; the function default provides a read-only semantic anchor if the core can traverse the loaded module/class dictionaries.

The loaded-module key is supported by a consumer import, not inferred from `co_filename`: MPK index `86590` (`gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_assist_aim.py`, decoded SHA-256 `d0fe9e911b355def749f5ecb6ff3ea1f9872002fb0ad00f854ba9c3efba99b11`) executes `IMPORT_NAME 'gclient.framework.util.assist_aim_util'` at offset 122, then imports `AssistAimMelee` and sibling names. This supports looking up the producer module under `LocalRootModules['gclient.framework.util.assist_aim_util']`. Both the producer and consumer import `CombatState` from `gshare.consts` (`IMPORT_NAME`/`IMPORT_FROM`/`STORE_NAME` offsets 118/120/122 for index 68262; 340/342/344 for index 14066). A direct mapping from that script import to `_gcommon.GameState.CombatState`, the enum's runtime type, and its integer encoding are not demonstrated by these modules.
