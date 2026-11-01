# Attribute dispatch boundary: faction and combat_state

Pinned PE SHA-256: ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747, verified before each native extraction. Disk-only PE and selected MPK parsing; no process reads, game execution, getters, descriptors or target bytecode execution. No ExternalCore/tests files changed.

## Discriminating result

**NumericMap represents stored replicated data; it does not by itself prove the value of host.faction or host.combat_state.** Both native and Python dispatch give normal attributes priority over the native property-map fallback. Thus operand_semantics_verified must remain false until the actual lookup path and possible shadows are validated. This audit does not establish a ready opponent filter.

Native Python entity base type796f3c0 receives tp_getattro1439f30 at9e3c9 (type+90), and tp_setattro143a080 at9e3d7 (type+98). The initializer and its SHA are pinned in upstream-sources.json.

### Native entity lookup

Callback1439f30:

1. Calls generic lookup2a0a1c0 on the host at1439f4e, passing no explicit dict and suppression=-1. Any result or error is returned; property fallback occurs only after a miss with no pending error.
2. Reads HostBridge=[Host+20]. If HostBridge+20 is null, it performs ordinary generic lookup on [HostBridge] at1439f75.
3. Otherwise, obtains MapPy=[HostBridge+18], performs generic lookup on that object at1439f8c, and returns a result/error if present.
4. Only after that miss does it call NativeMapGet12f5f60 on [MapPy+20] at1439faa.

This path uses the host bridge's cached property-map references. The separately recovered area.prop() callback reads NativeArea+1D8. Their pointer identity/lifetime is not universally established by this function. An observer using area.prop() storage must validate the relevant aliases when claiming the native-host route: MapPy equal to the host bridge's map, and matching backing pointers. These are observational coherence guards, not assignments proven here.

Native area_map getter12f94a0 independently follows generic-first, then native backing fallback at12f94eb. Generic CPython lookup prioritizes a data descriptor, then instance storage, then other class/non-data attributes. Source and native body are pinned through managed-models/native-exact-ranges.json and object.c. No descriptor was evaluated by this audit.

### Python ClientEntity route

The selected full framework streams show ClientEntity.__getattr__ (index66925, marshal4583) calling getattr(self.area.prop(),name), bytecode4-74. It is a fallback method; its presence does not override normal instance or class attribute resolution.

CPython's dunder hook body2a1dca0 was located by references to exact pinned Unicode __getattr__/__getattribute__ objects, not by an address guess. It looks up those names in the type, distinguishes the ordinary generic wrapper2a094d0 and a custom __getattribute__, and invokes __getattr__ after a missing-attribute path. The optional custom __getattribute__ call means that knowing only the native base type is insufficient to certify an arbitrary heap subclass's dispatch. See dunder-unicode-objects.json, getattr-hook-candidates.json and dunder-hook-contiguous.json. This identifies the source-pattern role; no exported symbol or runtime slot value was observed.

ClientEntity.__setattr__ routes names present in __property_all__ through setattr(self.area.prop(),name,value), else delegates to Entity.__setattr__. Native entity setter143a080 likewise checks registered property-name metadata, then either generic assignment or native property backing. A normal setter's routing does not remove read-side descriptor/instance shadows.

The framework Property function writes defaults and flags into class-local __property_all__ / __property_flag__ mappings (index32464, marshal18918, offsets204-244); it does not itself install a same-named Python property descriptor. PropertyMetaClass builds index metadata and generated initialization methods. This does not prove that another native base, metaclass, injected component or later assignment cannot supply a descriptor.

## Truth of the operands

Native helper2a09600 matches CPython truth dispatch:

| Priority | Data inspected | Action |
| --- | --- | --- |
| Singleton | True7a129b0 / False7a12990 / None7a0a150 | True / False / False |
| Number | [type+60], then number-suite+48 (nb_bool) | Calls slot if present |
| Mapping | [type+70], then suite+0 (mp_length) | Calls slot if present |
| Sequence | [type+68], then suite+0 (sq_length) | Calls slot if present |
| Default | No applicable slots | True |

These byte offsets are hexadecimal. Presence of a nonzero object pointer is not sufficient to emulate truth. A passive guard can establish default True only when the actual object's applicable slots are absent; an unrecognized nonzero slot remains unknown. No nb_bool/tp_len callback was executed. Negative callback results can signal an error and must not be silently mapped to false.

The native entity initializer sets as_number/as_sequence/as_mapping to NULL, so its base storage has default truth. PlayerCombatAvatar's effective heap type can acquire inherited or dynamic slots; that must be checked on the actual type rather than assumed from the base. The property-map object's possible __len__ is separate from the host operand's truth.

## Replicated value conversion

When dispatch actually reaches the supported NumericMap storage, fixed integer getter15539c0 produces a Python integer through32/64-bit conversion routines; fixed float getter15539a0 produces a Python float. Mixed storage1554880 dispatches tag0 to integer conversion and tag1 to float conversion; other tags may return Python objects or use lazy initialization. Those conversion paths do not prove which named attribute was selected beforehand. The descriptor+78 tagged handle remains opaque; it was not reclassified as a custom getter.

A raw faction integer and raw combat_state value can therefore remain useful state facts while effective Python operands remain unverified. In particular, this audit does not identify the CombatState enum encoding or replace its comparison semantics with an assumed alive/dead rule.

## Search scope and deliverables

Two additional complete modules were hash-verified and statically decoded: combat_avatar107853 and combat-unit component14066. Along with the three previously decoded framework modules, a bounded code-name audit found no direct definitions named faction, combat_state, __bool__, __len__ or __getattribute__. This is **not** absence from inherited native descriptors, generated assignments, injected methods or loaded runtime classes. The PE standalone NUL-terminated literal search for faction and combat_state returned no hits under its exact boundary rule; it does not establish absence of those properties.

python-dispatch-selected.json retains nine relevant class/framework code objects. Native instruction files include bytes, file offsets, RVAs and branch targets. upstream-sources.json pins reused source evidence by SHA-256. artifact-manifest.json pins this folder. Broader global scans were not added after the discriminating lookup boundary was established.
