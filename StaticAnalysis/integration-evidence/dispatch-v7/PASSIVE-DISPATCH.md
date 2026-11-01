# Passive dispatch V7: implementable acceptance rules

Pinned PE SHA-256 ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747 was verified before every native extraction. All addresses below are RVAs; object fields are hexadecimal offsets. No game/process reads, native calls, getters, descriptors or target bytecode execution. No core/tests changed. PASSIVE-DISPATCH-CONTRACT.json is the machine-readable contract; source-links.json and artifact-manifest.json pin inputs and outputs.

## What can now be accepted

A passive resolver can accept ordinary generic instance lookup, native Asio entity lookup, and the CPython __getattr__ hook **when it proves the known getter returns a value**. It can inspect static-builtin class dictionaries through the validated interpreter instead of treating them as empty. It must resolve the nearest actual IsEnemy, validate its binding and then apply the existing body fingerprint. It must not skip an override to find a matching ancestor.

This establishes acceptance rules, not an observed active method or effective game operands. The same rules must establish space.game_logic before treating that object's IsEnemy as active.

## Exact types and method forms

| Type | RVA | Relevant behavior |
| --- | --- | --- |
| type |7a15170 | tp_getattro(+90)=2a1db20, which jumps2a1d910 |
| function |7a135a0 | tp_descr_get(+110)=2a1a830, tp_descr_set(+118)=0 |
| method |7a273d0 | im_func+10, im_self+18; descriptor getter2b1dc30 returns itself |
| wrapper_descriptor |7a21e50 | d_type+10, d_name+18, d_base+28, d_wrapped+30; getter2aff3d0 |
| method-wrapper |7a21630 | descriptor+10, bound self+18; call2b00ad0 |

A normal function found in a class MRO binds to the instance: function getter2a1a830 calls constructor2b1d050 for nonnull self. Constructor2b1d0cf stores function+10,2b1d0e7 stores self+18, and its allocation path uses method type7a273d0 at2b1d147. No method allocation is needed to emulate the binding; retain the pair (function,self).

If an instance-dictionary override is already an exact method object, read those fields and require the expected bound self plus an exact function object. A raw function stored on an instance does not receive implicit binding. For the supported three-argument IsEnemy body, reject it, arbitrary callables, staticmethod7a138e0, classmethod7a13740 and unknown descriptors. A class-level method object also retains its original self; require matching self if supporting it.

All MRO dictionaries needed before the nearest hit must be inspected. Data-descriptor precedence comes before instance storage; generic lookup invokes a descriptor when its type has both get+110 and set+118. Native2afee60 tests set+118. Reject unsupported descriptors instead of treating them as absent. Other non-data descriptors require known semantics; exact function/method forms above are sufficient for the common Python method path.

## Static builtin class dictionaries

Exact helper2a1d600 proves:

- If !(T.flags+A8 & 0x2), dictionary=[T+108].
- Otherwise, index=u64(T+168)-1. Primary state is Interpreter+2BF38+0x30*index. If its type pointer matches T, use it. Native code can otherwise fall back to Interpreter+2E4C8+0x30*index for small indices. Dictionary is state+18.

Official pinned pycore_interp_structs.h gives primary capacity200 and extension capacity10. Therefore require index<200 for primary and index<10 for secondary, and require the chosen state.type+0==T. The native comparison permits index10 before secondary fallback, but the header's ten-element array supports only0..9; the passive contract rejects the extra case.

State layout from the header: type pointer+0, isbuiltin int32+8, readying int32+C, ready int32+10, dictionary+18, subclasses+20, weaklist+28; size30. Requiring ready1/readying0 is a conservative initialization guard. Header-derived initialized-count fields are Interpreter+2BF30 and +2E4B8, immediately before their arrays; they can further bound the index. Interpreter identity must come from the validated interpreter associated with the module/root context, not an arbitrary thread pointer.

If the state cannot be validated, return Unknown. Do not turn an unreadable STATIC_BUILTIN dictionary into an empty dictionary. MRO+158 itself remains a direct field; the source moves dict/subclasses/weaklist into per-interpreter state, not the MRO.

## Accepting the CPython getattr hook without executing it

Actual tp_getattro2a1dca0 is the recovered CPython dunder hook. Resolve __getattribute__ by raw class-MRO lookup, not ordinary instance lookup. Accept a precise wrapper descriptor form:

- Exact wrapper_descriptor type7a21e50; d_type is present in the object's MRO; d_name is __getattribute__.
- d_base points to the exact wrapperbase record **7a13e60**.
- d_wrapped is either generic2a094d0 or native entity1439f30. Reject arbitrary function/descriptor overrides.

The record7a13e60 pins name5812b40, slot offset90, slot function2a1dca0, trampoline2a224e0, flags0 and name object92687f8. Native method-wrapper call2b00ad0 fetches the trampoline from d_base+18 and sends d_wrapped as its third argument. Trampoline2a224e0 validates a one-element argument tuple, takes its name from tuple+20 and jumps to that wrapped getter. This proves the wrapper's effective native target rather than assuming it from the descriptor's name.

The hook consults __getattr__ but calls it only after the chosen __getattribute__ fails/misses. Consequently, a **positive known-getter result** does not require accepting the fallback __getattr__ body. This covers an IsEnemy function found normally, and a supported numeric operand found through native1439f30. If generic2a094d0 misses and a Python ClientEntity.__getattr__ fallback would be needed, leave it Unknown until that fallback body is separately verified. Unknown __getattribute__, descriptors or slots remain unsupported. The optional slot2a1dc70 is recorded but not necessary for this initial hook subset.

## Native cached-map aliases are now tied to a producer

The entity.area setter1439290 proves the cache assignments, conditional on a valid nonnull map:

```
H = [Host+20]
H+10 = AreaPy                         #1439325
AreaNative = [[AreaPy+20]]             #143933f/1439343
MapPy = [AreaNative+1D8]               #1439346
H+18 = MapPy                          #1439352
H+20 = [MapPy+20]                     #1439356/143935a
```

Thus H+20 is the cached native map backing pointer, not a boolean marker. Clearing area or assigning None zeros H+10/+18/+20 at14392e3..14392ed. If a newly assigned area's MapPy is null, branch1439350 skips overwriting the previous cache fields. This makes the observation-time alias checks mandatory: H+18==current MapPy and H+20==MapPy+20 backing, with nonnull supported backing, plus the previously proven area/host reverse links.

Native1439f30 performs generic host lookup first, then generic lookup on H+18, then NativeMapGet12f5f60. The middle step directly calls generic lookup, not the property's object's arbitrary tp_getattro. For faction/combat_state, reject unsupported descriptor/class/instance shadows at either generic step. Only after both steps miss may the supported typed NumericMap conversion establish the returned Python scalar. Do not use raw stored map values before those gates.

## Enum namespace and truth gates

For class-valued enum namespaces, require the **actual metaclass** tp_getattro equal to type getter2a1db20. That alone is insufficient: implementation2a1d910 first searches the metaclass for a same-named data descriptor (2a1d994,2a1da68,2a1da7b) before consulting the enum class MRO. Reject that shadow, or conservatively reject any same-named metaclass attribute. Require a positive raw class-MRO integer entry for each enum constant. A default type getter does not erase metaclass descriptor precedence.

Operand truth remains separate: native2a09600 checks True/False/None, then number.nb_bool, mapping.mp_length and sequence.sq_length. Default True is valid only when the actual relevant slots are absent. A supported NumericMap integer conversion returns an exact Python integer; unsupported object tags/custom comparisons remain outside this scalar contract.

## Evidence and limits

New instruction files include bytes, file offsets and branch targets; type-field-bytes.json pins complete type fields. Function/method construction, wrapperbase/trampoline/call chain, builtin dictionary selection, enum metaclass precedence and cache assignment all have local byte evidence. Official descriptor/class headers and the previously pinned interpreter header are hashed in source-links.json.

The callbacks were inspected as data. Static Asio type fields are initialized by startup routines, so their zero on-disk placeholders must not be mistaken for observed runtime slots. No live type slots, aliases, dictionaries or active IsEnemy were observed. A resolver can now produce a guarded positive when supplied a coherent supported snapshot; this report does not itself certify an opponent filter or executable aimbot.
