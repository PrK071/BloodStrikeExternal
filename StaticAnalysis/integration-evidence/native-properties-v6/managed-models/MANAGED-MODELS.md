# CPython 3.14 managed model attributes: disk-only proof

Target PE SHA-256 ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747 was rechecked by every native extraction script. No target process, native code, Python payload, getter or descriptor was executed. The deliverable is a layout contract for raw stored attributes, not an observed live object.

## Result

Both ordinary materialized managed dictionaries and valid inline instance values can be read from the pinned GIL build without calling CPython. managed-layout-contract.json contains the field contract. Official v3.14.0 headers and Objects/object.c / dictobject.c are retained with exact URLs and SHA-256 in sources.json.

The managed pointer is **plain PyDictObject* at object-0x18**, or NULL. There is no low-bit tag, pointer mask or extra indirection in this field. Do not import older PyDictOrValues rules. The GIL header sets MANAGED_DICT_OFFSET to minus3 pointer widths and weakref to minus4 widths. The free-threaded ABI uses different offsets and is unsupported here. The generic managed branch ignores tp_dictoffset; do not interpret a managed type's negative tp_dictoffset as an ordinary object offset.

## Native proof and dispatch order

Wrapper2a094d0 zeroes optional dictionary/suppression arguments and jumps2a0a1c0. Its body matches the pinned _PyObject_GenericGetAttrWithDict flow, including Unicode validation, type readiness and descriptor precedence, followed by instance storage.

At2a0a2e4 it reads type flags+0xA8. INLINE_VALUES mask0x4 selects helper2a8adf0 before any managed-dict fallback. At2a0a33a, MANAGED_DICT mask0x10 selects address object-0x18 (2a0a33e), dereferenced2a0a386. The corresponding materializer2a8cd70 directly loads object-0x18 at2a8cd76 and stores there at2a8cdb9/2a8cdeb. These bytes independently corroborate the source macro. No materializer is invoked by this analysis or required by a reader.

Use native-exact-ranges.json for the bounded actual functions. generic-contiguous.json intentionally includes adjacent exploratory code; it is not the selected function boundary.

## Valid inline values

For a validated supported heap type with MANAGED_DICT and INLINE_VALUES:

```
T = [Object+8]
V = Object + signed64[T+0x20]       # tp_basicsize, require positive/aligned/bounded
K = [T+0x370]                     # ht_cached_keys
```

PyDictValues is not a PyObject. Its capacity/size/embedded/valid fields are bytes at V+0/+1/+2/+3; its PyObject* values array starts V+8. Helper2a8adf0 computes V at2a8ae09/0d, checks valid byte at2a8ae10, loads K at2a8ae31 and returns `[V+8+8*index]` at2a8ae59. It obtains index through key helper2a94320, without taking a value from the key entry itself.

Native initializer2a8aaa0 sets capacity at2a8aad0, size0/embedded1 with word0100 at2a8aad4, valid1 at2a8aadb, clears pointer values, and initializes Object-0x18 to NULL at2a8aaf4. It derives capacity from the shared key object's usable+nentries fields. Header-derived capacity is at most SHARED_KEYS_MAX_SIZE30.

A small reader can enumerate shared keys instead of hashing:

| Field | Location |
| --- | --- |
| Shared key kind | byte K+0xA, require2 (DICT_KEYS_SPLIT) |
| Total index-table byte exponent | byte K+9 |
| Number of schema entries | signed64 K+0x18 |
| Unicode entry array | K+0x20+(1<<exponent) |
| Entry stride / key pointer |0x10 / entry+0 |
| Instance value | V+8+8*schema_index |

Compare only exact pinned compact-ASCII Unicode keys such as model. The key-entry value field is not meaningful for shared keys. Require capacity1..30, size<=capacity, nentries<=capacity, supported bounded key layout and valid1/embedded1 for this inline path. NULL at the matching instance slot means no stored instance value, not a callable fallback.

The shared-key offset is independently derived from official source: sizeof(PyTypeObject)=0x1A0; the ordered embedded method suites and ht_name/ht_slots/ht_qualname place ht_cached_keys at0x370. header-derived-offsets.json records all offsets and method-suite sizes; native2a8ae31 matches it. 05-header-offsets.py performs only layout arithmetic on header declarations using explicit Windows pointer/unsigned-long widths.

## Materialized dictionary and split values

With INLINE_VALUES, valid inline values take precedence even when Object-0x18 is non-NULL. That is the native generic ordering. If inline values are invalid, do not read stale inline storage: require an existing materialized dict at Object-0x18 and inspect that dict's own keys/values. If the pointer is NULL, leave the main-model link unknown rather than calling materialization.

A materialized dict may still be split and point to the same inline values. Materialization helper2a93560 stores keys at Dict+0x20 (2a93603) and values at Dict+0x28 (2a93607). Native dictionary lookup2a8bf80, preserved in dict-lookup.json, selects kind2 and reads `[Values+8+8*index]` at2a8c038/03c. Values points to PyDictValues, not a bare pointer array.

Two split-table rules matter:

- Shared-key indices describe all schema nentries. They do not have to equal this object's ma_used: other instances can share a key while this instance has a NULL value there. Do not reuse the combined-dict check that the number of referenced indices equals ma_used.
- The valid byte is meaningful for embedded values. Official new_values() initializes capacity, size and embedded0 but leaves valid uninitialized for standalone split values. Require valid1 when embedded1; do not test that byte for embedded0. Independently bound capacity, indices and value reads. A reader that does not implement nonembedded split values can explicitly leave that branch unknown.

Existing combined exact-dict handling remains usable when ma_values is NULL. No source or native function supports treating a split schema's entry+8 as the instance value.

## Main-model identity use

The intended checks compare stored object identities:

1. The native Asio host's ordinary stored model equals the AvatarModel instance already identified through IEntity.instance.
2. That AvatarModel instance's managed dictionary or inline model equals the same IEntity wrapper P.

The second equality can now be obtained from valid inline storage, not only a previously materialized dictionary. It excludes a stale native model only when the surrounding source and observed identity chain are also valid. Raw dictionary storage does not evaluate overridden getattribute, properties or data descriptors. This artifact supplies layout facts, without claiming every live AvatarModel has particular flags, tp_basicsize or a particular key index.

Unsupported flags/layout, invalid inline storage with no readable dict, missing keys, unexpected types and inconsistent repeated observations remain unknown. No core or tests were changed; all new files are confined to this managed-models folder. The unrelated2ab59f0 exploratory helper is not used as inline initialization proof; the correct initializer is2a8aaa0.

