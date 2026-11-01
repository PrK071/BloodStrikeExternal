# Active space and game-logic producer â€” V6 phase 4

Static-only MPK evidence tied to executable SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Selected streams were hash-checked and parsed through EOF. No game/process access, bytecode execution, runtime imports, or payload evaluation.

## Producer chain

MPK index `29779`, code filename `gclient/framework/entities/space.py`, decoded SHA-256 `0965992fef0dd6c69f1c4e17bd4d0c7152a2a43d8a6a631aef9b42291a06400e`:

1. The `Space` class is constructed with `ClientSpace` as its base (module bytecode offsets 964â€“996; `LOAD_NAME ClientSpace` at 970 immediately precedes the class build). The module imports that base from `client.ClientSpace` (offset 218, `IMPORT_NAME client.ClientSpace`, then `IMPORT_FROM ClientSpace`).
2. `Space.init(self, spaceno, spaceid, owner, ...)` initializes `self.game_logic` to `None` (`LOAD_CONST None` then `STORE_ATTR game_logic`, offsets 100â€“104). Later in the same method it executes `genv.space = self` (offsets 1368â€“1380: `LOAD_FAST self`, `LOAD_GLOBAL genv`, `STORE_ATTR space`). This is the concrete Python producer for the active global-space reference.
3. `Space.enter(self, entity, category)` checks `entity.IsGameLogic`; on the true branch it executes `self.game_logic = entity` (offsets 238â€“276: `entity.IsGameLogic`, boolean branch, fused load of `entity` then `self`, `STORE_ATTR game_logic`). Thus the active game-logic value is the entity that enters the space with `IsGameLogic` true, not a class inferred from the module name.
4. `Space.destroy` reads `self.game_logic`, calls its `destroy()` if present, clears `self.game_logic` to `None` (offset 1332), clears `ClientSpace._instance`, and stores `None` into `genv.space` (offsets 2048â€“2082). This establishes the teardown/reset path.

The field is initialized and later populated by Python stores on `Space`; however, `Space` inherits `ClientSpace`, which itself is imported from native-facing `client.ClientSpace`. The selected Python class bodies do not declare a `game_logic` property, but this static evidence does not establish that no inherited native data descriptor intercepts `STORE_ATTR` or takes precedence over instance-dictionary lookup. Therefore the logical producer and ordinary attribute reader are proven, while the exact external storage slot for `Space.game_logic` remains unproven.

## Consumer/getter path

MPK index `107853`, `gclient/gameplay/logic_base/entities/combat_avatar.py`, decoded SHA-256 `11babd1e40f2036808527dc7589df652ae108cc51e3c37f0259c951a6b09dd0d`: both `PlayerCombatAvatar.CheckAimTargetWhenStartAds` and `CheckAimTargetWhenRealAds` read `space = genv.space`, then `game_logic = space.game_logic`, gate on `game_logic.game_state`, and call `game_logic.IsEnemy(genv.player, entity)`.

MPK index `68262`, `AssistAim.SelectTarget`, reads `player = self.owner` and `player.game_logic.CanDamage(cur_result, player)`. The avatar member getter is independently explicit: MPK index `94048`, `CombatAvatarMember.game_logic` in `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_space.py` (decoded SHA-256 `43f2c0b7b45e52378b45920f44473b28d6b7219dbb64f1e7ab0c83ad0256fcae`) returns `self.space.game_logic` when `self.space` is truthy and otherwise returns `None` (offsets 2â€“68). The shared `AvatarMember.game_logic` does the same at index `38405`.

## Implementation identity gate

`IsGameLogic` is only the producer-side entity marker; it does not identify which override is active. A class-name whitelist is insufficient because `Components(...)` injects component methods onto host classes. The exact base implementation is `IGameLogicBase.IsEnemy` from index `108818`, code filename `gshare/game_logic/igame_logic_base.py`, raw code-byte SHA-256 `9cfb18d4557dce7c882bfc8df9a3ce7368b1e8a97abf786a0c15d59bf0b30219`. `IGameLogicBase.CanDamage` raw code-byte SHA-256 is `b23f2d62cdc634e101323bd51a3ee7f86a90523da99dbe3b1caebccf867f4eca`.

For a future strict base-mode gate, compare the runtime bound method's underlying `__func__`/code object identity or its raw `co_code` hash to the verified `IGameLogicBase.IsEnemy` reference; reject overrides whose code differs. This identifies the implementation, not the live mode by itself, and should be combined with the active object reached via `genv.space.game_logic`. For Peekaboo, its override has distinct code hash `23ba15b51dca4b6f9e4999199aa5822e82b7eead2944d94a6961e8ee34473b5a`; the MobaFaction override `MobaFactionMapInfoMixin.IsEnemy` has code hash `c3cd9518e161567d17b7fa72914ebffe6e5cf9b45e65e1c0f97590f8d21db33f`. A runtime policy can positively whitelist exact function code references for a chosen mode and reject other implementations.

## Machine evidence

`01_parse_space_logic.py` reproduces the bounded decode and full parse for indices `118280` (`engine/client/ClientSpace.py`), `29779` (`gclient/framework/entities/space.py`), `38405` (shared avatar-member `cimp_space.py`), and `94048` (combat-avatar-member `cimp_space.py`). `01-space-logic-candidates.json` retains compressed/decoded hashes, all selected complete code-object instruction streams, direct `STORE_ATTR` name resolution, and parse-to-EOF lengths. The selection was limited to these four semantically named modules; it did not repeat a 9,705-stream scan.

## Remaining boundary

The source path now establishes `genv.space -> Space.game_logic -> IsGameLogic entity` and reset behavior. It does not establish the native base-class descriptor behavior, a stable external address for the Python `Space` instance, nor a live mode. A passive reader can only use the instance dictionary route after proving descriptor precedence for `Space`/`ClientSpace`/native `SpaceClass`; a function-identity gate still needs the actual active logic object and its method reference.
