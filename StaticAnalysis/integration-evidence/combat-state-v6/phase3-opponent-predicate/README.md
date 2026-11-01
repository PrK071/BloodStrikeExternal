# Opponent and damage predicates â€” V6 phase 3

Static-only analysis of the pinned MPK inventory. Target SHA-256: `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. The parser verifies compressed/decoded digests and parses each selected stream through EOF. No game/process access, runtime import, or bytecode execution.

## General inherited contract

The module at MPK index `145546` (`gclient/gameplay/game_logic_base.py`, decoded SHA-256 `a3c7b11aa4a2d9ea8b52a6ee279859ef6e268e26aab3a5433aacc48078c5318c`) creates `CGameLogicBase` with `IGameLogicBase` as its base (module code offsets 616â€“636). `GameLogicBase` installs `CGameLogicBase` through `Components(...)` (module offsets 638â€“710), and `GameLogicBase.player` returns `genv.player` (line 296). Thus the general methods below are the inherited component implementation when no mode component overrides them.

MPK index `108818` has code filename `gshare/game_logic/igame_logic_base.py` and decoded SHA-256 `c69a1b41935d7a6f56bc7c43be13665325816d9ff5191624f963ee12a5c98af9`. Its module builds `IGameLogicBase` over `six2.with_metaclass(PropertyMetaClass, object)`; the class body installs `CanDamage`, `IsEnemy`, `IsFriend`, and `GetOption`. `options` is a `Property('options', CustomMapType, Property.ALL_CLIENTS)`.

- `IGameLogicBase.IsEnemy(self, a, b)` (line 129): identical objects return false; if either argument is falsey return false; otherwise either negative `faction` returns true, and if neither is negative it returns `a.faction != b.faction`. Branch targets are in the full instruction record. `COMPARE_OP` at byte offsets 76, 110, and 168 decodes to `<`, `<`, and `!=` respectively.
- `IGameLogicBase.IsFriend(self, a, b)` (line 140) returns `not self.IsEnemy(a, b)`.
- `IGameLogicBase.CanDamage(self, a, b)` (line 122) reads `self.GetOption(OptionKey.DamageTeammate, False)`. If truthy it returns true for all arguments; otherwise it returns `self.IsEnemy(a, b)`. `GetOption` (line 147) is `self.options.get(name, default)`. So the option/property state is an explicit dependency of damageability.
- `CGameLogicBase.IsTeammate(self, a, b)` (index 145546, line 169) is a separate helper, not the inverse of a universal faction rule: identity returns true; missing inputs return false; for nonnegative factions it compares equality, while its negative-faction branches are asymmetric. The complete CFG is retained below; use the mode's actual `IsEnemy`/`IsFriend` contract for opponent classification rather than substituting this helper.

## Mode overrides are separate scopes

`GameLogicMobaFaction` in MPK index `92227` (decoded SHA-256 `0aa075d290f14b0da643885faad1c91ce41ee45a1b8ad4c7e76c19d92fef8ed7`) is built with `MobaFactionMapInfoMixin` first in its bases and `GameLogicMoba` second. `GameLogicMoba` is a subclass of `GameLogicBase` (index `85021`, decoded SHA-256 `a1e5beb0c1d178e3d2c4992b7176f20d961bb2c10edeb3ad6ce74f91e21f1a55`). The mixin overrides:

- `MobaFactionMapInfoMixin.IsEnemy(a,b)` (line 205): identity/missing checks; calls `GetEntityFaction` for each argument; if either result is `None`, calls `super().IsEnemy(a,b)`; otherwise negative faction on either side returns true, and otherwise it compares faction inequality. It is not the base implementation because it maps entities through `GetEntityFaction` first.
- `IsFriend` (line 218) performs identity/missing checks then returns `not self.IsEnemy(a,b)`; `IsTeammate` (line 225) delegates to `IsFriend`.

`GameLogicPeekaboo` in MPK index `132180` (decoded SHA-256 `0ffe6ae378af23c4f6f63847128a6562ec1bad78100965952a1d2bbcaed1d5a1`) installs `CGameLogicPeekaboo` with `Components(...)`. Its component overrides:

- `IsEnemy(a,b)` (line 68): identity/missing checks, then compares `getattr(a, 'peek_role', 0) != getattr(b, 'peek_role', 0)`.
- `IsTeammate(a,b)` (line 76) returns false.
- `CanDamage(caster,target)` (line 95) calls `IGameLogicBase.CanDamage` directly, then flips a true result only when both `caster.is_finder` and `target.is_finder` are truthy. This preserves the base option and enemy logic while adding a mode-specific finder/finder restriction.

An auxiliary zombie component is in the machine report, but it is outside the requested general/Moba/Peekaboo scopes. It likewise demonstrates why a fixed cross-mode rule is unsafe. The selected consumers read the active game-logic reference as `genv.space.game_logic` (PlayerCombatAvatar ADS methods, index 107853) or `self.owner.game_logic` (`AssistAim.SelectTarget`, index 68262); those accesses provide the concrete mode-gate path. Phase 4 later identifies the producer: `Space.enter` stores the `IsGameLogic` entity in `self.game_logic`, while `Space.init` publishes `self` to `genv.space`. Runtime/native descriptor precedence and external storage location remain unproven.

## Opcode decoding and evidence files

`03-general-and-mode-predicates.json` stores each selected whole code object: local names, globals/attributes, constants, every instruction offset, and relative branch target. `COMPARE_OP` was decoded using the pinned CPython 3.14 encoding, not the raw argument integer:

- operator index is `oparg >> 5`; `oparg & 16` is the bool-conversion flag. This is documented in [CPython 3.14.0 Lib/dis.py](https://github.com/python/cpython/blob/v3.14.0/Lib/dis.py#L588-L591) and implemented by `_COMPARE_OP` in [CPython 3.14.0 Python/bytecodes.c](https://github.com/python/cpython/blob/v3.14.0/Python/bytecodes.c#L2455-L2471).
- The operator table is in [CPython 3.14.0 Lib/opcode.py](https://github.com/python/cpython/blob/v3.14.0/Lib/opcode.py#L22). Relative branch target decoding follows `dis.py`'s instruction resolver.

`01_literal_scan.py` and `01-literal-scan.json` record a hash-checked bounded search over all 9,705 candidate streams. There were no literal hits for `EnemyFilter`, `modeCache`, or `mode_cache`; this only establishes absence of those exact names in this scan, not absence of semantically equivalent code. The `diagnostic` hits were not used as evidence of a classifier.

`02_parse_predicate_candidates.py` / `02-predicate-code-candidates.json` preserve positive candidate selection; `03_general_mode_predicates.py` regenerates the full selected records and checks the target and stream hashes. In particular, the `COMPARE_OP` records carry operator, bool-result flag, and the low opcode flags; all branch targets are derived from the decoded instruction metadata.

## Runtime contract boundary

These functions establish game-code semantics, but a passive external reader still needs the active game-logic object and its mode/component implementation, plus entity/property inputs. The `CanDamage` contract additionally needs `options[OptionKey.DamageTeammate]`; the Moba contract needs `GetEntityFaction`; Peekaboo needs `peek_role` and `is_finder`. This evidence does not establish a stable external address/layout for those calls or prove the live mode. Do not assign authoritative opponent/ally labels from faction equality alone.
