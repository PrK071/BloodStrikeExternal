# Python owner storage: V5 static evidence

The pinned PE was hash-verified before analysis: SHA-256 ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747. All addresses below are RVAs unless they are object-relative fields. Only on-disk PE and official CPython sources were inspected. No game process, target code or target bytecode was executed. Existing RawPE/iced-x86 decoding was reused; REA tools are not registered in this agent inventory.

## Strong result: P+0x10 is a demonstrated dictionary slot for the PyIEntity factory

This is no longer an assumption based on neighboring fields:

1. Existing RTTI catalog names COL70124a0 as Messiah::PyIEntity. In the pinned PE, its COL pointer immediately precedes vtable57859b0. Validated RIP-relative LEA references locate constructor20335c0 and factory20391f0. The latter calls type getter2052480, allocates using its +130 slot, clears Python P+10/+18/+20/+28, and installs the RTTI-linked C++ wrapper into P+20 at203931e. P+8 is read as type at2039326. C++ wrapper initialization2d85a60 stores native pointer at W+18. The existing RTTI catalog supplies the class label; this pass reconfirms pointer linkage and raw bytes, not the complete RTTI hierarchy independently.
2. Getter2052480 returns type storage79a0060. Instruction20525ab explicitly sets [79a0180]=0x10, which is type+120 = tp_dictoffset under the pinned 3.14 GIL ABI. This type has file-backed basicsize0x30. Initializer2052556 writes flags0x14400, which excludes managed-dict and inline-values flags.
3. Registration2059800 installs a getset record with name __dict__ at string547acd0 and getter1ccfa30/setter1cd57c0. The getter loads P+10 at1ccfa36; when null it calls2a88dd0 and stores the result into P+10 at1ccfa47. This independently anchors the declared dictionary offset to executable access, rather than relying on header naming alone.
4. Dictionary constructor2a88dd0 calls allocator2a93930 with zero values pointer and used count, and empty keys7a198c0. Allocator writes D+28 values, D+20 keys, D+10 used, D+18 watcher tag=0. Allocation's static dict type is7a19900, whose name is dict and basicsize0x30.

Evidence: entity-vtable-xrefs.json, entity-type-initializer.json, entity-ready-contiguous.json, dict-accessors.json, dict-constructor.json, dict-allocation.json, builtin-type-identities.json. The ready function crosses several unwind fragments; 09-ready-full.py therefore preserves the exact bounded contiguous range2059800..205998a. The shorter08 result alone is incomplete.

This proves storage design for this factory. It does not show that every Parent wrapper is PyIEntity, that every live P has completed readiness, or that every dynamic owner write uses the dictionary: effective inherited tp_setattro/tp_getattro remain untraced. They begin as zero in this type initializer. Registration2075900 calls readiness2a1cab0. Its optional tp_base comes from the registered factory in2084900 result+38; following1ce16f0 reaches base getter1ccccd0 (storage7995be0), with the same dictionary offset10. Effective generic-slot inheritance is still a separate unresolved control-flow question.

## Pinned minimal layout contract

layout-contract.json records numeric offsets and source URLs/hashes. These are source-derived ABI fields for Windows AMD64 LLP64, little endian, CPython3.14.0 without Py_GIL_DISABLED. The sample corroborates ob_type+8 through allocator2a1cb10:2a1cbef, type alloc+130 through both factories, and 32-bit refcount operations at object start. Its static heads also carry the 3.14 immortal-reference encoding and type pointer at+8. This supports the GIL layout in these objects; no claim of a whole-program build-configuration audit is made.

| Structure | Fields needed |
| --- | --- |
| PyObject | type+08; header size10 |
| PyTypeObject | name+18; basicsize+20; itemsize+28; getattro+90; setattro+98; flags+A8 (Windows unsigned long32); base+100; dict+108; dictoffset+120 (signed64); mro+158 |
| PyDictObject | used+10; watcher tag+18; keys+20; values+28; size30 |
| Keys | log2_size byte+08; log2_index_bytes byte+09; kind byte+0A; version uint32+0C; usable signed64+10; nentries signed64+18; indices+20 |
| General entry kind0 | stride18; hash+00; key+08; value+10 |
| Unicode entry kind1 | stride10; key+00; value+08 |
| PyASCIIObject | length signed64+10; hash+18; state uint32+20; data+28 when compact ASCII; kind=(state>>2)&7, compact bit5, ASCII bit6 |
| Tuple/MRO | count signed64+10; cached hash+18; item pointers+20 |

All hex fields in this table use the ordinary non-free-threaded ABI. Unicode compact ASCII requires kind1, compact1, ASCII1; validate exact ASCII payload and terminating zero within bounded length. A C string from tp_name is a different layout. Do not reuse old 3.10/3.11 Unicode offsets.

Entries begin at K+0x20+(1<<K.byte09). The exponent describes total indices bytes, not per-index width. Limit exponent, nentries, capacity and arithmetic before any read; scan entries only through nentries and skip null/deleted entries. Sample lookup2a8bf80 confirms kind byte+0A, exponent byte+09, general value address K+(1<<byte09)+0x30+24*i and Unicode value K+(1<<byte09)+0x28+16*i. See dict-lookup.json. Fields nentries/usable and Unicode state masks are header-derived, not independently demonstrated by this native function. Tuple type7a18ce0 has name tuple, basicsize20 and itemsize8; its sequence sq_item slot resolves to2a823b0, which bounds against count+10 and reads item at+20+8*i (2a823bf). This confirms the new3.14 cached-hash layout; old tuple item offset18 is incorrect. Type type7a15170 has name type and its own ob_type points back to itself. See tuple-type-and-item.json.

A deliberately narrow reader can require exact dict type base+7a19900, ma_values==0, kind0 or1, positive bounded dictoffset and no INLINE_VALUES(4)/MANAGED_DICT(16). Reject kind2/split, negative or zero dictoffset, virtual descriptors and unsupported Unicode formats. Require expected wrapper identity and consistent native/Python backlinks independently. Exact dict type avoids subclass behavior ambiguity.

Type flag STATIC_BUILTIN(2) needs special care when reading tp_dict: sample readiness2a2e990 uses interpreter-specific side storage for flagged builtin types, instead of type+108. Reject or skip such type dictionaries; do not treat null direct tp_dict as an empty dictionary. The wrapper initializer14400 does not set this flag. Iterate a bounded validated MRO tuple in order; a direct dictionary hit is evidence of the stored marker, not proof of all descriptor/getattribute semantics. Arbitrary monkey-patched classes remain outside a raw-storage interpretation.

## True/False: primary byte evidence, no guessed integer payload decoding

The PE export name table was checked for selected PyBool/PyObject/PyDict APIs and singleton names; none of those selected names appeared. python-export-identities.json records the bounded names and count. Instead, static bool type7a127f0 has tp_name bool and tp_new2a14310. That body selects7a12990 initially, calls truth helper2a09600, returns null on negative result, and selects7a129b0 on nonzero result. This matches the pinned CPython bool_new source, preserved as boolobject.c. Both singleton heads point to bool type7a127f0; raw heads are retained in singletons-and-heads.json. Thus True can be conservatively matched by pointer base+7a129b0 and False by base+7a12990 for this exact hash, without decoding lv_tag/digits. This is a source-pattern plus type-slot linkage, not an exported PyBool_FromLong symbol identification.

## Integration boundary

A successful guarded observation of a direct instance-dict owner value would close that observed P-to-owner storage edge. A marker IsPlayerCombatAvatar whose stored value equals the proven True singleton can support a PLAYER category if its class/MRO provenance is validated. It does not establish team, enemy status, health, visibility or that every actor Parent follows the same path. No core reader or tests were implemented in this pass.

Remaining exact uncertainty: effective attribute slots and any data descriptors that shadow owner; actual live wrapper type and readiness; coherent dictionary/MRO snapshots; and the universal relationship between ActorComponent.Parent and the model entity carrying owner. These are not replaced by a fabricated offset.

## Sources and reproduction

Seven official headers and one bool implementation were downloaded from the CPython v3.14.0 tag. header-sources.json and artifact-manifest.json pin local byte hashes. Primary URLs include https://raw.githubusercontent.com/python/cpython/v3.14.0/Include/object.h, Include/cpython/object.h, Include/cpython/dictobject.h, Include/internal/pycore_dict.h, Include/cpython/unicodeobject.h and Include/cpython/tupleobject.h beneath the same tag; complete URLs are in header-sources.json.

Run numbered scripts with the configured Python runtime. Each script that opens the PE verifies the pinned SHA. Searches for vtable references/direct calls are limited to supported LEA/E8 encodings in executable sections and validated against instruction boundaries within unwind records. These searches cannot prove whole-program completeness or identity of unobserved heap objects. 07-type-callers.py retains repeated caller rows for distinct callsites; repeated entries are not independent corroborations. No files outside python-owner-v5 were intentionally written by this work.

