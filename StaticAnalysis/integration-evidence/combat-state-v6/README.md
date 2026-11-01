# Gameplay combat-state contracts — V6

Date: 2026-11-01. Static analysis of MPK Python streams on disk only. Executable snapshot pinned to SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. No game launch, process/memory access, payload import/eval, or bytecode execution.

## Contracts demonstrated

### Local-player producer and reader

`gclient/gameplay/logic_base/entities/combat_avatar.py` (MPK index `107853`, decoded SHA-256 `11babd1e40f2036808527dc7589df652ae108cc51e3c37f0259c951a6b09dd0d`): `PlayerCombatAvatar.init_from_dict` stores `self` into `genv.player` (bytecode offsets 6–18), `genv.main_player` (50–62), and `GlobalData.p` (72–84). `PlayerCombatAvatar.destroy` clears `genv.main_player` and `genv.player` only after `IS_OP` identity checks against `self` (offsets 98–212). `GameLogicBase.player` in `gclient/gameplay/game_logic_base.py` (index `145546`, decoded SHA-256 recorded in the machine report) returns `genv.player` (offsets 2–32).

The reader has a replay branch: `gclient/framework/util/replay_util.py`, `GetPlayer` (index `86897`) returns `genv.player` for the ordinary/non-replay path and conditionally returns `genv.replay_player` in replay paths (offsets 34–288). Therefore a single-player identity test based only on `genv.player` is not justified for replay. The actor class marker `IsPlayerCombatAvatar` only classifies the Python class; it does not by itself identify the local instance.

### Enemy/opponent consumers

`PlayerCombatAvatar.CheckAimTargetWhenStartAds` and `CheckAimTargetWhenRealAds` are the strongest player-target consumers in `combat_avatar.py` (lines 450 and 485). They require PC + ADS + active game state, raycast from the gameplay camera, resolve `Body.ownerid` through `space.GetEntity`, require a truthy entity with `IsCombatAvatar`, reject `IsRobotCombatAvatar`, then call `game_logic.IsEnemy(genv.player, entity)` (first function offsets 894–948). A true result sets `genv.is_last_avatar_aim=True`; the second method then may call `genv.avatar.CallServer(..., AntiAdsCheck)` after its angle/aim gates. This is a semantic opponent predicate call in game code, not a field classifier. Both ADS methods establish the active-object access path explicitly: `space=genv.space`, `game_logic=space.game_logic`, then `game_logic.game_state` and `game_logic.IsEnemy(...)`. `AssistAim.SelectTarget` independently reads `self.owner.game_logic.CanDamage(...)`. Phase 4 identifies the producer: `Space.enter` stores the entity whose `IsGameLogic` marker is true into `self.game_logic`, and `Space.init` publishes `self` to `genv.space`. Runtime class and native-descriptor precedence remain unresolved.

`GameLogicEnemyShowStateComp.TickEnemyDistanceForShow` (index `76499`, SHA in machine report) calls `replay_util.GetPlayer()`, iterates `self.space.combat_avatars`, invokes `self.IsEnemy(avatar, player)`, then uses the two positions and `DISTANCE_FOR_SHOW_ENEMY_EFFECT` to add/remove `tech_state_enemy_distance_show_id`. `AssistAim.SelectTarget` (index `68262`) gets `player=self.owner`, calls `player.game_logic.CanDamage(cur_result, player)`, restricts candidates by `IsCombatAvatar` or eligible monster flags, `IsAssistAimTarget`, supplied `combat_states`, range/visibility, then picks by dot/distance. This is a second explicit targetability contract that requires the game's `CanDamage` call.

### Team/ally is mode-dependent

`CGameLogicBase.IsTeammate(a,b)` in `game_logic_base.py` (line 169, offsets 2–228) handles identity and missing objects, then compares the two objects' `faction` values. Its bytecode does not read `combat_team_id`. The initial phase-1 wording about undecoded comparisons is superseded by phase 3, which decodes CPython 3.14 `COMPARE_OP` from `oparg >> 5` and records complete branch targets. The negative-faction branches of `IsTeammate` are asymmetric; do not treat it as a universal same-faction predicate.

Confirmed mode-specific overrides make a universal `combat_team_id` equality rule unsafe:

- `MobaFactionMapInfoMixin.IsEnemy(a,b)` in `logic_moba_faction/game_logic_moba_faction.py` (index `92227`, line 205) calls `GetEntityFaction` for each side and falls back to `super().IsEnemy(a,b)` when faction information is missing. `MobaFactionMapInfoMixin.IsTeammate(a,b)` (line 225) delegates to `IsFriend(a,b)`.
- `CGameLogicPeekaboo.IsEnemy(a,b)` in `logic_peekaboo/game_logic_peekaboo.py` (index `132180`, line 68) reads each `peek_role`; `IsTeammate` (line 76) returns literal `False`.
- `SquadFightCombatAvatarToplogo._IsEnemyFor1v1Logic` (index `78274`, line 176) has a special branch for states `1v1Prepare` / `battling_1v1` using `combat_team_id` and the `battling_1v1` mapping, excluding the current battling player. This is a specific 1v1 UI rule, not the generic enemy rule.
- The `IGameLogicFreeForAll` code object (index `3779`) exposes round/score/state properties and a `proto` getter but no `IsEnemy` or `IsTeammate` implementation among its code objects. Its presence does not prove how FFA enemy/faction semantics are supplied; do not assume equal IDs mean allies there.

### Health and life-state data

`CombatAvatarMember.hp` (index `14066`, line 266) returns `self.server_hp` directly. The `CombatAvatarMember` class descriptor declares `server_hp` as a replicated `Property('server_hp', float, Property.ALL_CLIENTS)` (class-body offsets 434–472). `PlayerCombatAvatarMember._on_set_server_hp` emits `events.ON_CHANGE_HP`; `_on_set_maxhp` also emits that event with `self.hp` (class member callbacks around lines 989/993). `HudTeamInfoComp.OnCombatTeamMemberMaxHpChange(pid)` forwards the member-info key `'maxhp'` (index `2597`, line 239). These show health-change/UI producers, but this pass did not locate a direct `is_alive` property contract or prove the schema/ownership for `maxhp`.

`AssistAim.SelectTarget` explicitly reads `cur_result.combat_state` and rejects states in its `combat_states` argument. Thus `combat_state` is a demonstrated state filter; it should not be replaced by a guessed `hp > 0` test.

## What a pure external data reader can and cannot classify

Reusable V5 model evidence shows a Python `IEntity` wrapper has `.owner` assigned to the gameplay `area`, and `.instance` assigned to its `SimpleModel`; `AvatarModel` owners can carry class tag `IsPlayerCombatAvatar`. The existing V5 `ClientEntity.__getattr__` evidence forwards unresolved fields through `self.area.prop`, and `Entity.init_from_dict` calls `self.area.prop._initProperty(...)`. Given the unresolved native `ActorComponent.Parent` → wrapper handoff, an external reader can only use these once that parent/wrapper mapping is established.

After it reaches the same entity/owner/property object, fields demonstrated in this pass include `combat_state`, `faction`, `combat_team_id`, `server_hp`, and the class marker. The local reference is separate global state (`genv.player`, with replay-specific switching), and opponent/ally decisions call `game_logic.IsEnemy`, `IsTeammate`, `IsFriend`, or `CanDamage`. Those methods are not reproduced by the fields alone and can vary by logic subclass/mode. No offsets are inferred here.

**Classifier contract supported by this evidence:** entity/class marker can nominate player-avatar candidates; properties can expose replicated state; opponent/ally/local decisions require the active game-logic/local-player context and its semantic methods. A pure field-only reader can report candidates/state but cannot claim authoritative enemy/ally/local labels from `combat_team_id` or the class tag alone.

## Reproducible evidence

- `01_semantic_modules.py` / `01-semantic-modules.json`: hashes, full parse-to-EOF records, exact selected code objects and resolved opcode windows; `STORE_ATTR` uses direct `co_names[arg]`, while `LOAD_ATTR` / `LOAD_METHOD` / `LOAD_GLOBAL` use `arg >> 1`.
- `02_scan_semantic_literals.py` / `02-literal-positive-indexes.json`: bounded literal scan of all `9,705` indexed streams, verifies compressed and decoded hashes and stores positive indexes for semantic terms.
- V5 context: `../gameplay-classifier-v5/README.md`, `../gameplay-classifier-v5/11-corrected-owner-store-attr-audit.json`, `../gameplay-classifier-v5/13-model-instance-discriminator.json`, and `../gameplay-classifier-v5/14-avatar-model-module-identity.json`.

All V6 files were written only beneath `StaticAnalysis/integration-evidence/combat-state-v6/`; no core or tests files were changed.

## Exact opponent-predicate implementation

See [phase 3 predicate evidence](phase3-opponent-predicate/README.md) for the full `IGameLogicBase.IsEnemy` / `CanDamage` bodies, inherited `CGameLogicBase` relationship, decoded CPython 3.14 comparisons, branch targets, and distinct MobaFaction and Peekaboo overrides. The active-game-logic value is read from `genv.space.game_logic` by the player ADS consumers and from `owner.game_logic` by `AssistAim`; phase 4 establishes its producer. A pure data reader must obtain that same active object and mode-specific semantics before issuing an authoritative opponent/team label.

## Active game-logic producer

See [phase 4 space/game-logic evidence](phase4-space-logic/README.md). Space.init stores its Python self in genv.space; Space.enter stores the entering IsGameLogic entity in self.game_logic; player ADS and AssistAim consumers then read that value. The logical source/consumer chain is concrete, while native-descriptor precedence and the external storage slot for Space.game_logic remain unresolved.

