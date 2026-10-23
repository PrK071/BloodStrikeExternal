# MPK asset-header inventory (audit-v4)

Scope: offline disk inspection of `Engine.mpkinfo` and `Resources.mpkinfo` from the Steam installation path recorded in `payload-inventory.json`. This inventory was produced for target build context Steam build 25981220 / patch 126 / executable SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`; the MPK indexes themselves do not independently encode that build identity. Index SHA-256 values are recorded below. This was not process inspection and did not interact with the game or anti-cheat.

## Index and sampling totals

The candidate parser treats each index as an 8-byte `<II` header (version 4 and candidate row count), followed by `<QQII` rows (24 bytes each) and a 16-byte trailer. The candidate interpretation assigns fields as opaque ID, offset, size, and flags; flags bit 0 is treated as a directory candidate and `flags >> 1` as package index. All candidate payload ranges fit their package sidecars, but this verifies bounds only, not the semantics of those fields or compatibility beyond the on-disk target named above.

| Index | SHA-256 | Candidate rows | Directory candidates | Non-directory, nonzero headers sampled |
|---|---|---:|---:|---:|
| Engine.mpkinfo | `457db446eee8dd6fcc9bfbb600f1561f44750b0625ab4278dc353fc404a3d376` | 56 | 7 | 49 |
| Resources.mpkinfo | `bb3782da03b95d66451a598add8fe0923405be0dde53a8844b2f8bc107a6ced3` | 201,388 | 4,100 | 197,287 |
| **Total** | — | 201,444 | 4,107 | **197,336** |

Exactly the first 32 bytes (or the full payload if smaller) were read for each of the 197,336 non-directory, nonzero entries. Reads were coalesced by nearby ranges to reduce I/O; no payload was extracted as a tree.

## Header observations

`Resources.mpk` payload prefixes include 96,924 `ZZZ4` markers, 63,374 `02 02 02 01` markers, 23,014 `.MES` prefixes, 2,854 `BKHD` prefixes, 9,836 `E2 06 ...` prefixes, 5 text/JSON-like prefixes, and 1,280 other prefixes. These are raw prefix classifications only: `ZZZ4` and `E2 06` were not decompressed or decoded, `.MES` is only the four-byte prefix of a longer candidate marker, and opaque IDs were not converted to names.

`Engine.mpk` has 29 `META` prefixes, 3 JSON/text-like prefixes, 1 XML-like prefix, and 16 other headers. Bounded reads of the 29 `META` payloads expose generic PhysX serialization/schema strings such as `PxActorFlags`, `Sc::ActorCore`, `ActorSim`, and `NpConnector`. Keyword checks on these `META` strings yielded no `player`, `character`, `entity`, `component`, `skeleton`, `animation`, `python`, `lua`, or `script` strings. This is evidence only about these Engine metadata payloads, not all game resources or runtime types.

Three small Engine text/config payloads were read in full (all <=1 MiB):

- Entry 10, package 0, offset 746,204, size 158: XML font configuration naming Consolas and Cascadia Code.
- Entry 15, package 0, offset 1,299,782, size 105,355: JSON with 2,677 top-level keys; labels include editor terms such as Components, Skeleton Updated, Character, Skeleton Path, Animation, Entity, and Play Animation.
- Entry 17, package 0, offset 1,405,137, size 58,478: JSON with 548 top-level keys; labels include `Common_CopyComponent`, `EntityTree_*`, `Window_Components`, and `Window_Skeletontree`.

The two JSON payloads appear to be editor/UI localization dictionaries based on label structure. They expose vocabulary, not a serialized actor/component schema, player/NPC classifier, or runtime object producer.

Two small Resource candidates were also inspected in full because their raw prefixes justified a bounded structured-data read (both <=1 MiB):

- Entry 201,291, package 26, offset 314,973,750, size 14,373: starts `7b 73 23 00` (`{s#\0`); visible text includes `UIScript/auto_og_patch_scene_new0_ui.plist` and hash-like paths. Structure and meaning remain unresolved; this is not evidence of Python source.
- Entry 201,385, package 26, offset 346,746,844, size 16,779: JSON `file_list` mapping shader paths to metadata. It is an asset/cache inventory, not gameplay object metadata.

Two further Resource payloads look JSON-like at the sampled prefix but exceed the 1 MiB inspection limit, so only headers were read: entry 193,599 (17,527,297 bytes) and entry 201,386 (8,774,345 bytes). No claims are made about their bodies.

## Python and script signature result

Among exactly 197,336 sampled payload headers, the count was **zero** for each tested signature at byte offset 0: Lua bytecode magic `1b 4c 75 61`, a `#!` shebang, and a CPython-style one-byte magic followed by `0d 0d 0a`. This is a zero observation for those raw leading signatures only. It is not functional absence: source scripts need not have a shebang; bytecode signatures vary by version and container; scripts could be embedded after a wrapper or inside compressed/encoded payloads. The scan did not search/decompress payload interiors, infer filenames from opaque IDs, or attempt decompilation.

## Relevance and limits

This sample does **not** identify a public or on-disk source that classifies players/NPCs, defines `GetAllActors`, `ActorComponent`/`Parent` relationships, generates `AnimationCore::Skeleton` IDs, or supplies camera/transform semantics. Engine localization mentions those concepts in editor-facing labels, but that cannot establish runtime layout or behavior. The `META` payloads appear to document generic PhysX serialization types; they do not identify Blood Strike gameplay producers.

The candidate index layout and flag interpretation remain hypotheses despite clean bounds. Payload type labels are prefix-level observations, not format specifications. No bulk decompression, full extraction, bytecode decoding, or execution occurred. There were 34 bounded full-payload reads in total, all no larger than 1 MiB: 29 `META` entries, 3 Engine XML/JSON text/config entries, and 2 Resource structured-data/JSON entries. The 29 `META` reads are additional to the five small text-like/config/manifest reads listed individually above.

## Follow-up targets for static analysis

1. Inspect the already identified Engine localization dictionaries only to trace editor terminology to nearby static metadata; do not treat labels as runtime definitions.
2. Analyze small, clearly textual manifests/indexes offline for filename/path semantics, starting from Resource entry 201,291 and the bounded JSON `file_list` at 201,385; retain hashes and exact entry references.
3. For the two large JSON-looking candidates, defer body inspection unless a specific research need justifies a separately bounded read. Do not broaden to full archive extraction.
4. Continue static searches in the target executable and verified target-build metadata for cross-references to candidate actor/component/skeleton/camera symbols. Any offset or behavior from another build remains non-evidence for this target until independently matched.

Machine-readable counts, index hashes, candidate references, and uncertainty notes are in [payload-inventory.json](payload-inventory.json).


Reproduction assets are in [reproduction/](reproduction/). The copied probe_mpk_v4.py is the saved local script for index candidate parsing and bounds checks; it produced mpk-candidate-probe.json, not the full header inventory. The script used for the coalesced 32-byte inventory and bounded payload triage was an inline, unsaved probe, so no exact source script for that pass is available to copy. The recorded Python runtime was C:\Users\luiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe; the probe otherwise uses only Python standard-library modules. No script was rerun for this correction.

