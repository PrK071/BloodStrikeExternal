# Native ClientPlayer / IGameplay link and static model evidence

Pinned PE SHA-256: `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747` (confirmed by `01-link-probe.json`, `04-clientplayer-methods.json`). Evidence is static; no target process was accessed or executed.

## ClientPlayer.Char: what closes and what does not

The PE contains the reflected-name string `Messiah.ClientPlayer.Char` at RVA `0x51c47e0`. The adjacent reflection data includes the names `ClientPlayer` and `Char` and a code pointer at `0x51f9170` to RVA `0xce4570`. That function decodes to `lea rax,[rcx+0xea0]; ret` (bytes `48 8d 81 a0 0e 00 00 c3`), so this is a concrete address accessor for a `ClientPlayer` member at offset `+0xea0`; it returns the member address, not the member value.

`ClientPlayer` RTTI is at COL RVA `0x6ea2828` and lists bases `IPlayer`, `IStoryboard`, `IComponent`, `IObject`, and `IInputFilter`. Its constructor-like function at `0xa76b40` writes null to `[rbx+0xea0]` (`48 89 bb a0 0e 00 00`) and to `[rbx+0xec0]` (`48 89 bb c0 0e 00 00`). This corroborates pointer/member storage at both offsets but does not identify their C++ types. A nearby accessor at `0x6a5850` returns `this+0xec0` and is adjacent to the following `ClientPlayer.Signal` metadata, so it should not be conflated with `Char`.

RTTI names include `PyClientPlayer::BindChar`'s lambda and an inner lambda call operator accepting unsigned `I` (32-bit). This is consistent with an input-character notification; absent a code/data cross-reference that maps the callback to this property, that remains context only. The direct `Char` accessor does not establish `Character::Actor`, `ActorComponent`, or an `IPlayer` pointee. No static chain from `IGameplay.Player` to `ClientPlayer.Char` was found.

`Messiah::IPlayer` and `Messiah::ClientPlayer` are distinct RTTI classes; ClientPlayer derives from IPlayer. `Character::Actor` is a separate RTTI class deriving from `AnimationCore::Skeleton` and `Messiah::IRefObject`. `Messiah::ActorComponent` is also separate (it derives through `SkeletonComponent`/`ISkeletonComponent`). Their names or shared use of “Actor” do not prove an object link.

## IGameplay.Player

The reflected name is at RVA `0x4f501e0`. The neighboring accessors support a property stored at `IGameplay+0x58`: `0x58b020` returns `this+0x58` (`48 8d 42 58 c3`), `0x92bec0` reads `[this+0x58]` (`48 8b 41 58 c3`), and setter `0x948bd0` replaces `[rbx+0x58]` (`48 89 7b 58`) and notifies for old/new non-null values. The setter is a generic pointer-valued property accessor. This establishes neither concrete pointee type nor a producer assigning `ClientPlayer`; the `ClientPlayer` and `IGameplay` strings have no code xref chain connecting them. `IPlayer` RTTI describes a gameplay interface, but its name alone cannot classify instances or distinguish human players from NPCs.

The parent-state finding `Parent.IsInWorld` is a lifecycle/state predicate. It is not type or team evidence and is intentionally not duplicated here.

## Static Python model links

Input: `../python-format/selected-models-static.json`, SHA-256 `0493a5c510cc06a998d4888777696e14195ed947ef7f7be144414017cd58aa9a`. The four parent-selected marshal records are consumed as already-decoded static JSON. No bytecode was run. The extraction script and its bounded output are in `python-model-links/`.

The strongest object-construction path is in `gclient/framework/util/MHelper.py`, selected resource index `17226`:

- `LoadSkeletonAndGraph`, code object marshal offsets `[11385,12517)`, line 261, tests `isinstance(instance.Skeleton, MObject.ActorComponent)` at bytecode offsets 132–202. In the branch that creates the object, offsets 216–258 execute `LOAD_GLOBAL MObject; LOAD_ATTR CreateObject; LOAD_CONST "ActorComponent"; CALL 1; STORE_ATTR instance`; it then calls `instance.Skeleton.LoadSkeletonAndGraph(...)` at offsets 270–322. The alternate branch constructs `"SkeletonComponent"` at offsets 466–520.
- `BindSkeletonAndGraph`, code object offsets `[52367,53704)`, also calls `MObject.CreateObject("ActorComponent")` (bytecode 80–122) and later calls the skeleton-loading path; its alternate branch constructs `"SkeletonComponent"` (312–354).
- `CreateModel` in this same module calls `LoadSkeletonAndGraph` at bytecode offsets 712–736. This supplies a static bridge from the generic model factory into the native ActorComponent constructor path.

Generic `SimpleModel` (resource index `68957`) calls `MHelper.CreateModel` in `SimpleModel.Load` at bytecode 816–854 and stores the returned result in `self.model` at 1826. `SimpleModel.ReloadSkeleton` starts from `self.model.Skeleton`, checks it with `isinstance(..., MObject.ActorComponent)` at offsets 54–104, obtains its `ActorParent` at 118–148, and may call `AddChild` at 608–640. `SimpleModel.HasActorComponent` directly returns `isinstance(self.model.Skeleton, MObject.ActorComponent)` at offsets 50–140. These are real load/call/field-use sequences, not name-only hits.

`WeaponModel` (index `25281`) declares `SimpleModel` as its base in the module-level `LOAD_BUILD_CLASS` sequence (offsets 232–252). Its initializer calls `super().__init__` (bytecode 4–42), and its hand-attachment methods call `hand_model.model.Skeleton.AddChild(model.Skeleton)` (e.g. `AttachWeaponToHandEquip`, offsets 178–302) and then `AttachToParent`. This links weapon models to the generic SimpleModel path and shows their skeleton objects are used as children/attachments; it does not imply weapons are players.

`AvatarModel` (index `143510`) declares `PoseSenderModel` as its base (module bytecode 1030–1050), not directly `SimpleModel`. `AvatarModel.Load` calls `super().Load(...)` (offsets 6–46) and later tests `model.Skeleton.__class__ is MObject.ActorComponent` (offsets 638–694). In the same method, branches use `owner.IsCombatAvatar`, `owner.IsATMGuardAI`, and `owner.IsPlayerCombatAvatar` (e.g. offsets 808–906 and 1124–1230), which are explicit classification predicates attached to the avatar owner. The four selected records do not include `PoseSenderModel`'s implementation, so the transitive factory chain through that intermediate class is not proven here; it can be resolved by statically parsing that additional resource.

`DestroySimpleModel` and `DestroyCppModel` in `MHelper.py` traverse `Attachments` and call `Parent.Detach()` (e.g. offsets 130–178 and 530–578). This confirms attachment/lifecycle use of `Parent`; it does not make Parent a player classifier.

## Limits and next static target

These records prove that a single named native `MObject.ActorComponent` is created by the shared model factory and is consumed by generic model and weapon code. Avatar code independently checks that same native type and applies owner-level predicates, while its full superclass factory chain remains open because `PoseSenderModel` was not among the selected modules. None of this establishes that every ActorComponent is a character/player, nor yields a runtime list of actors, team labels, or a player/NPC discriminator for arbitrary world objects.

Next useful static target: parse the already-indexed `gclient/framework/models/posesender_model.py` and any `PlayerAvatarModel` subclass module with the parent's marshal parser, preserving the same no-execution workflow. For the native `IGameplay.Player` property, trace setter callers and reflected registration code until an actual argument type or construction/ownership edge is proven; current generic property accessors are insufficient.
