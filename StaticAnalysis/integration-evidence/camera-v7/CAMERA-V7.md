# Native viewport camera: V7 result

The new independent render path connects `Player.Camera` to a separate native camera owned by `SceneViewportClient` and passed into `MainRenderViewport`. It provides an implementable typed read route. It does not establish final presented-pixel projection conventions or close the earlier shader-context alias.

All target operations were disk reads and native disassembly of pinned SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. No protected process, game execution, engine call or input was used. No core/test or earlier evidence files were changed.

## Implementable route

```
state     = ptr(module_base + 0x80f3840)
client    = ptr(state + 0x08)       # exact SceneViewportClient vptr 0x4e632f0
viewport  = ptr(client + 0x18)      # exact MainRenderViewport vptr 0x52f0498
effective = ptr(viewport + 0x50)
```

Mandatory cross-checks: `[viewport+0x740] == client`, `effective == client+0x80`, and matching pinned native types. COLs confirm zero object displacement for these exact vptrs. Addresses are RVAs above except the indicated object-relative offsets. Global construction/lifetime is not established; null, stale, unexpected subtype or alias mismatch must reject acquisition.

`read_effective_camera.py` is a reference implementation against a caller-supplied reader factory and pinned module identity. It performs two fresh observations, validates all type/alias gates, reads dimensions and finite stored projection data, and rejects unsupported camera types. `19-reference-check.py` passes six synthetic recording checks: positive typed Aurora, wrong vptr, two broken aliases, unsupported orthographic storage, and changed projection. No live reader is constructed by these files.

## Discriminating proof

The implementation-facing evidence is deliberately small: `effective-camera-contract.json` and `discriminating-native-evidence.json`. Large `seeds.json` / `main-provider-root.json` catalogues are exploratory coverage, not required implementation input.

1. Function `0x5fc290` allocates a `0x750`-byte viewport. At `0x5fc385` it loads global `0x80f3840`; at `0x5fc393` it passes `[state+8]` to constructor `0xdb8c90`, then registers the result with the renderer dispatcher at `0x5fc3b3`.
2. `0xdb8c90` calls provider slot `+0x50` and keeps that returned camera in RDI. Exact `SceneViewportClient` vtable `0x4e632f0` has slot `+0x50 = 0x3afcf0`, which returns `client+0x80`. The constructor passes this pointer through `0xdb7870` to `0xdb7110`; instruction `0xdb7153` writes it into `viewport+0x50`.
3. That constructor stores the provider into `viewport+0x740` at `0xdb8d02`. It calls provider slot `+0x80` with the viewport at `0xdb8d15`. Exact `SceneViewportClient` slot `+0x80 = 0x293980`, whose body writes `[client+0x18]=viewport`. It finally installs exact `MainRenderViewport` vptr `0x52f0498` at `0xdb8d2c`.
4. Exact `SceneViewportClient` slot `+0x90 = 0x343040` calls its virtual slot `+0xb8` at `0x343150`; that slot is `0x343ef0`. The latter reads the same global → gameplay+0x58 → player+0x58 → camera+0xd88 chain established earlier. It copies the source's 48-byte `+0x41c` matrix into client `+0xee0`, selects/configures the embedded native camera at `client+0x80`, and applies the copied matrix through camera slot `+0x68` at `0x3442ab`.
5. Source viewport dimensions are synchronized with the client's active dimensions through `0x276280` (writes ICamera `+0x408/+0x40a`); native render-camera resolution is set through slot `+0x128`. `RenderViewport` resize function `0xdb74f0` stores viewport uint16 width/height at `+0x18/+0x1a` and updates its camera pointer `[viewport+0x50]` through that same resolution slot.

This proves a configuration/update connection to the camera attached to a native render viewport. The source ICamera and effective render camera are separate objects; their pointers should not be compared for equality. The alias checks above identify the separate native render input.

## Camera selector and stored matrix

The selector first examines source ICamera `+0x450` (`UseAuroraCamera`, named in the preceding camera-binding reflection evidence). If nonzero it constructs `AuroraCamera` at the embedded address. Otherwise source `+0x418` selects `Orthographic3dCamera`, with `PerspectiveCamera` as the remaining branch. Source `+0x419` also enables extra projection parameters copied through further virtual methods. Never infer the actual subtype solely from source flags: read the current effective vptr.

| Effective exact vptr RVA | Native type | Slot +0x70 output |
|---:|---|---|
| `0x4ec0658` | AuroraCamera | getter `0x493c00` copies 64 bytes from camera `+0x6b4` |
| `0x4ebf848` | PerspectiveCamera | getter `0x485230` copies 64 bytes from camera `+0x2d8` |
| `0x4ebfaa0` | Orthographic3dCamera | getter `0x4876a0` computes output; no fixed equivalent storage proved |

Type identities are confirmed with native constructor vptr installs and COL/TypeDescriptor bytes. Source and effective near/far/FOV gates, projection subtype changes and orthographic parameters are shown in `viewport-client-selector.json`; projection getters are in `projection-storage.json`. The reference reader conservatively rejects orthographic storage.

The copied slot `+0x70` output is projection data, not a claimed combined view-projection matrix. The old CameraProjection writer calls a camera slot `+0x70` and copies the result to its render block `+0xfa0`; its specific camera/context alias to this viewport remains unproved. Matrix dimensions do not establish row/column vector multiplication, handedness, clip depth range, jitter, viewport offsets, screen/display scaling or final pixels. These fields are explicitly unresolved in the contract.

## Lifetime and scope limits

The update returns early when gameplay or source camera is absent; the effective camera can retain previous state. A verified code path does not establish scheduling, freshness or absence of later overrides. Two matching read observations likewise do not prove lifetime, atomicity or absence of ABA. Keep source and effective captures separate and expose these limits.

`12-unwind-regions.py` follows native CHAININFO to join actual split unwind regions. In particular `0xdb7ac0` has three associated regions and `0xc46ca0` five; a decoder stopping at the first unwind end would omit relevant bodies. The selected typed route does not rely on equating neighboring functions or guessed structure sizes. `unwind-groups.json` retains region identities and exact instruction bytes.

The earlier name `GetMainCameraViewProjection` is not sufficient evidence of final render selection: its callback constructs a temporary 2048×2048 perspective camera. It remains separate from the independent viewport route described here.
