# Re-derivação de offsets para um novo build

O cheat é **preso à build** do jogo (SHA-256 + offsets). Quando o Steam atualiza
o Blood Strike, nada mais lê a memória até os offsets serem re-derivados.
Este documento é o procedimento usado para mover da build `ff080393…` para a
`24c1ba6e…`, reproduzível para as próximas.

## O que muda entre builds

- `IMAGE_SIZE`, `SHA-256` do `BloodStrike.exe`
- RVAs dos *globals* (engine root, actor registry, render state, interpreter head)
- RVAs dos *type descriptors* (RTTI) de IGameplay, ClientPlayer, ICamera, IEntity
- RVAs dos *vtables* (render camera: SceneViewportClient, MainRenderViewport, camera avatares)
- RVAs de objetos CPython no painel nativo

Offsets de **struct** (posição dentro do objeto, ex.: `root+0x58`, `camera+0xD18`)
em geral **não mudam** num patch pequeno.

## Ferramentas (em `C:\Users\luiz\km_cheat\`)

- `analyze_static.py` (do repo, `StaticAnalysis/`) — inventário PE/RTTI/xref.
  Roda com Python 3.12 + `pefile` + `capstone`:
  `python StaticAnalysis/analyze_static.py --binary <BloodStrike.exe> --out <dir>`
  Gera `rtti-types.json`, `code-xrefs.json`, `core-vtables.json`, etc.
- `find_global_refs.py` — disassembla o `.text` do **mapped-image antigo** e lista
  instruções que referenciam um RVA de global.
- `match_globals.py` / `match_func.py` — faz *masked byte-match* de uma função
  antiga (wildcard nos deslocamentos RIP) no binário novo e extrai o novo alvo.
- `find_render_vtables.py` — acha o vtable novo de uma classe (scan de COLs em `.rdata`).
- `validate_live.py` — abre o jogo e valida cada RVA novo (lê ponteiros/strings).

## Procedimento

1. **Mapped image do build antigo** já fica em
   `reports/live-*/BloodStrike.mapped-image.bin` (dump virtual do build anterior).
   Ele contém o código e os dados do build **velho**, essencial para o match.
2. **Análise do binário novo**: rode `analyze_static.py` no `BloodStrike.exe` atual.
3. **Type descriptors** (fácil): procure o nome da classe em `rtti-types.json`
   (`Messiah::IGameplay`, `Messiah::ICamera`, `Messiah::IEntity`, …). O
   `type_descriptor_rva` é o novo valor. Confirme lendo `rva+0x10` no jogo (o
   nome mangled inline).
4. **Globals** (médio): com `find_global_refs.py` ache uma função velha que
   referencia o global; com `match_globals.py` mascare-a e procure no binário
   novo; o novo `mov [rip+disp],...` dá o RVA novo. Confirme lendo o ponteiro.
5. **Vtables** (médio): `id_vtables.py` diz a classe de um vtable velho
   (COL → type descriptor → nome). `find_render_vtables.py` acha o vtable novo
   procurando o COL cujo `td` == novo type descriptor.
6. **Validar ao vivo** com `validate_live.py`: leia o ponteiro/string em
   `base + rva`; ponteiro tem que estar em faixa válida, string tem que bater.
7. **Atualizar o código**: `camera_capture.py`, `registry.py`, `render_camera.py`,
   `python_runtime.py`, `rtti.py`, `entity_position.py`, `capture_live_build.py`,
   `native/rook.cpp` (IMAGE_SIZE, SAMPLE, RVAs). Rode `capture` e `watch` pra
   confirmar frames + atores.

## Offsets da build `24c1ba6e…` (validados ao vivo)

```
engine_root        0x80E5D70
actor_registry     0x8B8D490
render_state       0x8104100
interpreter_head   0x9270328
IGameplay TD       0x7E45028
ClientPlayer TD    0x7E670B0
ICamera TD         0x7DF5D90
IEntity TD         0x7DF5DB8
SceneViewportClient vtable 0x4E722F0
MainRenderViewport  vtable 0x52FFA58
AuroraCamera        vtable 0x4ECF668
PerspectiveCamera   vtable 0x4ECE858
Orthographic3dCamera vtable 0x4ECEAB0
IMAGE_SIZE         0x94FA000
SHA-256            24c1ba6e75e0028b74e3a34ebc2808b90ed014713dda874b5adc719b83ceead1
```

## Pendências conhecidas

- **Painel nativo (Aeon)**: falta re-derivar o bloco CPython (`0x925F000`-`0x925F010`
  → deslocamento `+0x11000` → `0x9270000`-`0x9270010`) e os RVAs de objetos CPython
  (`0x7A1B1F0` builtins dict, `0x7A0A150` replay sentinel) e type descriptors de
  entity/area (`0x796F3C0`, `0x796C240`). O cheat em Python já funciona sem eles.
- **Calibração de mira**: `calibration.json` foi medida em FOV 50 (ADS). Fora
  desse zoom/arma o aim desliga (`calibration_fov_mismatch`); refaça a medição
  por arma em `native/calibrations/` ou no painel.
