# V6 phase 2 — shape of `AvatarModel.owner`

Date: 2026-11-01. Static disk-only analysis. Target PE SHA-256 is `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. No game launch, process/memory access, payload import/eval, or bytecode execution. This phase only resolves the Python/native object boundary; it does not edit or rewrite the sealed V5 artifacts.

## Finding

`AvatarModel.owner` is assigned the value of `self.area`, where `self` is the entity host object to which the gameplay component method has been attached. The code evidence shows `self.area` is the separate native area proxy/property exposed by the Asio entity base, not the Python `PlayerCombatAvatar` host instance itself. Consequently, V5's proposed direct `mro(owner)` lookup for the `IsPlayerCombatAvatar` tag is **not supported**. The class tag is set on the Python host class; V5's native area attribute read may bridge to that class or its registration, but the direct MRO path is not established.

### Why `self` is the host

`combat_avatar.py` (index `107853`, decoded SHA-256 `11babd1e40f2036808527dc7589df652ae108cc51e3c37f0259c951a6b09dd0d`) builds `PlayerCombatAvatar` as a subclass of `CombatAvatar`; `CombatAvatar` is built from `ClientAreaEntity`. Its module applies `Components(...)` to the class. `classutils.py` (index `32464`, SHA `7e25e3c1907b728ce029281a72888ba35e85dd56923cb593383c134903e7f071`) shows `Components.<locals>._Components` obtains the host class, applies `ComponentHost(klass)`, and invokes `klass._addComponent(component)`. `_addComponent` copies component methods/descriptors onto that `klass` using `setattr(klass, name, ...)`. It does not create a per-component instance for `InitAvatarModel`.

In `cimp_model.py` (index `61925`, SHA `04bde99e6e2715d32cacce94496d4aba3f89919aae650d513a5468da1e790f4c`), `CombatAvatarMember.InitAvatarModel` evaluates `self.area`, `self.area.position`, and `self.area.yaw`, then calls `AvatarModel(self.area, position, yaw)` (bytecode offsets 38–142). Thus `self` is the bound host object; the first constructor argument is its distinct `.area` value.

### Why `.area` is not the host

`engine/common/Entity.py` (index `119023`, SHA `a6ef435ce5cefa8d72529fded95e670f44ba1224c39f6e51e658cd64ca4d0ac9`) creates `Entity` with `with_metaclass(EntityMetaClass, getattr(asiocore, 'entity', object))`. `Entity.__init__` initializes entity state/ID/timers and never assigns an `area` Python attribute. `engine/client/ClientEntity.py` (index `66925`, SHA `a36404ae9ebdfc46e3512f5e5d62b5bd6cf3ad4cbaa831a9166fce1dd4e97051`) derives `ClientEntity` from this `Entity`, and `ClientAreaEntity` from `ClientEntity`. Its constructor only calls the superclass constructor and sets `_space`; neither class defines an `area` Python property or stores `area` in a Python setter.

`ClientEntity.__getattr__` and `__setattr__` explicitly use `self.area.prop()` for property access. `Entity.init_from_dict` also initializes `self.area.prop()._initProperty(...)`. The separate native PE artifacts identify an `area` type/member table and a `prop` getter (see `../native-properties-v6/native-area-names.json`, `area-method-table.json`, `prop-and-area-accessors.json`; `prop` metadata at RVA `0x796ba70`, getter at RVA `0x130a140`). These are consistent with `.area` being an Asio-native area proxy supplied by the native `asiocore.entity` base, not the Python host instance. The metadata exposes property access; it does not by itself prove Python-class MRO behavior.

### Tag lookup and remaining boundary

The tag originates on the host class: `combat_avatar.py` applies `with_tag('IsCombatAvatar', 'IsPlayerCombatAvatar', 'is_fps_avatar')` before building the `PlayerCombatAvatar` class. `AvatarModel.Load` then reads `self.owner.IsPlayerCombatAvatar` (V5 index `143510`, offsets `1146` and `1348`). `ClientEntity.onEntityClassRegistered` calls `asiocore.regist_class(klass.__name__, klass)` (index `66925`), which is a plausible registration/dispatch bridge. The static Python evidence does **not** show how native area attribute lookup maps that registered host class onto an area proxy. It therefore supports this narrower conclusion: the property read is performed on the native owner proxy and the class tag lives on the Python host class; some native/class-registration lookup bridges them, but direct `type(owner).__mro__` inspection is not proven to reach the tag.

No parsed Python path in `Entity`, `ClientEntity`, `ModelComponent`, or `CombatAvatarMember` reads `owner.owner`, calls `area.get_entity`, or returns the PlayerCombatAvatar host from the area. The focused PE name inventory for the native area exposes `area`, `area_map`, and `prop`; it did not expose an `owner` or `get_entity` name. Do not synthesize an inverse reference from these files.

## Classifier correction

- **Keep:** the Python host class has `IsPlayerCombatAvatar=True`; the model's `owner` receives `self.area`; the owner-side bytecode reads `owner.IsPlayerCombatAvatar`.
- **Withdraw as unproven:** `mro(owner)` directly finds the `PlayerCombatAvatar` class tag.
- **Usable external contract:** to use that tag, a reader must reproduce the native area attribute/registration dispatch or recover the registered host class relation. The current disk artifacts do not show a pure pointer-only, MRO-based resolution for this relation.

## Evidence files

- `01_owner_shape_static.py` / `01-owner-shape-static.json`: parses only MPK indices `107853`, `117964`, `119023`, `66925`, `32464`, and `61925`; checks compressed/decoded SHA-256; parses to EOF; resolves `STORE_ATTR` directly through `co_names[arg]` and load attributes through `arg >> 1`.
- Native area references above are reused without modifying their artifacts.
- This folder is the only write target for this phase; no V5/core/test files were edited.
