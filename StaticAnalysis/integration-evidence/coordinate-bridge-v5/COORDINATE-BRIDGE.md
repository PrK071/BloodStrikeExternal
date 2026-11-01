# Coordinate bridge V5: precise static result

Pinned on-disk PE SHA-256 verified again: ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747. Static files only; no game execution, process access or target bytecode execution. Existing RawPE/iced-x86 decoder reused. REA MCP tools are absent from the current inventory; no PE reimport or tool installation was performed.

## Proven producer path

Upstream camera-binding/screenpoint-callers-static.json, module71683, CommonTopLogo.Create (marshal7550): on the existing-toplogo branch, instructions892–996 call formula.Tuple on self.mark_toplogo_ientity.Transform.translation and store self.mark_toplogo_pos. The other creation branch repeats the same attribute chain at2088–2192. The entity comes from MHelper.CreateDummy(pos), call242 and store252, and may be attached to another entity at424–466. Therefore this is a dummy entity's Transform.translation property, not a demonstrated actor GetEntityPosition result.

CommonTopLogo._UpdateMarkToplogo (marshal16356) loads that stored attribute4–24, resolves Player.Camera34–106 and passes Vector3(*mark_toplogo_pos) to GetScreenPointFromWorldPoint at156–216. No integer-origin arithmetic occurs in this producer-to-call chain. The method also loads camera.Transform.translation108–154 but does not use it in that argument.

A material restriction: after storing native screenPos224, this exact function unconditionally calls GetScreenPointFromWorldPointPython228–250 and unpacks its return258 into x/y/z262–264. The presence of both formulas does not prove they are numerically equivalent, nor prove that the native result determines this caller's visible mark. The fallback subtracts camera.GetOrigin; identifying that with camera+7c solely because the formulas look similar is unsupported.

Selected complete instruction streams and upstream resource digest are retained in selected-producer-flow.json. This pass consumes the earlier validated static decoding rather than executing/importing it; it does not independently revalidate those MPK bytes.

## GetOrigin binding: bounded dead end

Upstream native-origin-blocks.json links the literal Messiah.ICamera.GetOrigin (RVA4f6adc8) to records around4f449e0 and4f53d60. Directly decoding the following referenced code addresses produced only argument-shuffling sequences ending call16d810 and int3:

940a00,940a20,940a80,940aa0,940ac0,940ae0,9408d0,940910,940960,940bf0,940bd0,940c10,9407d0.

Bytes, file offsets, instruction RVAs and branch targets are retained in origin-initial-wrappers.json and origin-wrappers.json. These sampled callbacks do not load camera+7c or an anchor and do not supply a member-cell dispatch like the proven native screenpoint wrapper. The shared callee16d810 was not semantically classified, so this report calls them stubs rather than assigning exception/error behavior. This is a negative result only for those13 callbacks; it does not establish absence of a GetOrigin implementation elsewhere, inherited implementation, dynamic registration or alternate module.

## Exact unresolved conversion

Known separately: entity helper8977b0 returns P = double(T_e) + A_e, with the collective all-INT_MAX sentinel rule. Native screenpoint275db0 consumes float3 Q and computes float32(Q - C), where C is camera+7c/+80/+84; it does not read anchors. The newly recovered caller establishes Q originates from a Transform.translation property, but does not establish that property's native getter, concrete subobject adjustment or how its frame relates to P.

The missing equality is precisely Q = float32(P - O_frame), together with identification of O_frame and proof that C is expressed relative to that same O_frame. If the entity Transform getter is proven to return the same raw T_e with the same object adjustment as8977b0, then Q=T_e for that object follows. Extending that to arbitrary actor/camera pairs still requires proof that their local frames share origin (or the exact origin difference). Neither subtraction of camera anchor nor substitution of entity anchor is proven here.

Conditional algebra alone: if absolute camera position is C+A_c and entity absolute position is P, preserving relative displacement requires Q=P-A_c. If A_e=A_c, this reduces to Q=T_e. These are conditions for a future proof, not an implemented or established conversion. In particular, float32(P) passed directly to screenpoint cannot be certified from the present evidence.

The next evidence needed is the native implementation of IEntity.Transform.translation (including concrete type adjustment) and the assignment/rebase relation between entity anchorA_e and camera frame originA_c. The GetOrigin sampled records do not provide that relation. No core/tests files were changed and no external pipeline is declared functional.
