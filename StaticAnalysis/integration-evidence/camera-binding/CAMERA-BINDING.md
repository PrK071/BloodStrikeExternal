# Camera Python → controller → câmera de gameplay

Data: 26/10/2026. Inspeção estática de recursos em disco, sem importar/executar bytecode alvo, executar jogo ou acessar processo. Os hashes comprimidos e decodificados foram reconferidos contra o índice existente. Amostra PE de referência: SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`.

## Resultado

Foi fechado um elo que faltava em `python-camera/PYTHON-CAMERA.md`: há caminho explícito em `gclient/framework/entities/camera.py` (índice **87163**) que constrói placers com **master = instância Python Camera**, cria `MObject.CreateObject('CameraController')` para seu `controller` e associa esse controller a **MEngine.GetGameplay().Player.Camera**. Isso sustenta o vínculo por chamadas/atribuições Python/binding; não fornece offsets C++ nem prova qual câmera/viewport é usada na passagem final de renderização.

Os offsets abaixo são bytes de `co_code`, não offsets de memória ou RVAs. As referências completas estão em `binding-selected.json`; desassemblagem integral em `binding-disassembly.txt`.

## Cadeia comprovada local

1. `Camera.ConfigAimPlacer` (marshal **33030**), offsets **24–58**, resolve `BasePlacer.GetPlacerType('AimPlacer')`; **68–70** passa `self` ao construtor retornado; **78** passa o placer a `self.SetPlacer`. O `BasePlacer.__init__` já auditado guarda o argumento como `self.master`. Logo, nesse caminho, o master recebido pelos placers é essa instância Camera. A resolução de classe depende das subclasses carregadas e de globals Python não substituídos.
2. `Camera.LoadFromData` (marshal **35156**) repete o padrão com o nome `data['placer']['Type']`: seleção em **24–86**, construtor com self em **96–98**, `SetPlacer` em **106**. Não é apenas igualdade de nomes.
3. `Camera.Attach` (marshal **14061**) retorna cedo quando is_actived é verdadeiro (**32→42** corresponde ao ramo falso, **38–40** retorna no verdadeiro). Caso contrário, marca is_actived, grava **genv.camera=self** em **56–68** e chama **InitController** em **78–100**. Depois ativa special_placer ou placer, condicionado à presença do objeto.
4. `Camera.InitController` (marshal **9307**) chama **CreateController** em **4–24**; chama `controller.EnterArea(MHelper.GetActiveWorld().DefaultLevel.RootArea)` em **34–156**; carrega **MEngine.GetGameplay().Player.Camera** em **166–226** e grava **self.controller.ControlledCamera** em **246–268**. Depois cria collider e shaker.
5. `Camera.CreateController` (marshal **10573**) chama **MObject.CreateObject('CameraController')** em **2–36**, grava o retorno em **self.controller** em **44–46**; carrega **genv.hud_camera** e grava **controller.AffiliatedCamera** em **56–108**; grava **controller.IsDynamic=True** em **118–142**.
6. `Camera.engine_camera` (marshal **6158**) retorna diretamente **MEngine.GetGameplay().Player.Camera** em **2–82**. `Camera.position` (marshal **5867**) lê a mesma cadeia e retorna **Transform.translation** em **82–122**.

Com a evidência anterior de AimPlacer.OnActive, a cadeia local fica:

`Camera.ConfigAimPlacer → GetPlacerType('AimPlacer')(Camera self) → placer.master = Camera self → master.controller = CreateObject('CameraController') → master.controller.ControlledCamera = GetGameplay().Player.Camera → master.controller.BlendInPlacer(native placer, blender)`.

São acessos dinâmicos separados a propriedades Python; a inspeção não presume identidade estável através de callbacks, monkey patching ou execução concorrente. O `ControlledCamera` refletido como ICamera, já preservado em python-camera/native-property-blocks.json, corrobora a interface declarada desse binding. Não tipa por si só os campos internos de Player nem demonstra ponteiro externo.

## Câmera afiliada e viewport: separação concreta

`ClientEnv.InitHudCamera` (índice **40877**, marshal **19190**) chama **GetGameplay().Player.AddAffiliatedCamera('HUDCAMERA')** em **2–84**, configura FieldOfView=50, Near=0.01, Far=200 e retorna `c` em **136–138**. Este corpo retorna o objeto; a atribuição do retorno a genv.hud_camera não foi fechada nesta etapa.

`ClientEnv.AddModelAppearCamera` (marshal **19539**) cria outra câmera pelo nome **ModelAppearCamera**, modifica seu Transform e chama **MRender.AddAffiliatedViewport('ModelAppearCameraViewport','ModelAppearCamera',800,600,0)** em **260–302**, depois de remover viewport homônimo. Portanto existe um vínculo explícito de câmera afiliada com viewport **nesse caminho de apresentação de modelo**. Os 800×600 não são dimensões comprovadas da câmera principal ou da tela de gameplay. A semântica nativa do último argumento 0 não foi inferida.

## Bloqueio exato para integração externa

A origem lógica foi reduzida a **GetGameplay().Player.Camera** e a associação explícita a **CameraController.ControlledCamera**. Faltam:

- Resolução nativa de GetGameplay → Player → Camera, com layouts/indireções sustentados e lifetime; os atributos Python não produzem offsets nativos.
- Prova de que esse ICamera alimenta a passagem final/viewport principal, inclusive resize e câmeras alternativas.
- Ligação por fluxo ao bloco CameraProjection: a igualdade de blocos ainda ausente em camera/CAMERA-IDENTITY.md continua ausente. A cadeia Python não estabelece que Player.Camera é `[[arg2_escritor+8]+0x10]`, ou que sua saída é o bloco lido em contexto+0xb8/+0xfa0.
- Getter/escritor sustentado de matriz final e convenções de projeção, divisão por W e clipping.

Consequentemente, esta evidência não autoriza um leitor externo funcional nem um world-to-screen real. A próxima investigação nativa útil parte dos bindings **GetGameplay / Player.Camera / CameraController.ControlledCamera**; não de novo rastreamento de stores +0xb8 sem tipo.

## Cobertura e reprodução

`02-find-master.py` pesquisou apenas os quatro termos CameraMaster, CameraController, ControlledCamera, AffiliatedCamera nos **9.705 streams já indexados**, **188.383.211 bytes** decodificados no agregado. Cada stream teve hashes reconferidos. **CameraMaster não ocorreu** nessa cobertura; isso não prova ausência em streams excluídos, overlays ou construção dinâmica. Sete streams tiveram outros termos positivos, preservados em literal-camera-bindings.json.

`01-decode-binding.py` selecionou somente índices 7375,40877,87163 e consumiu **343 code objects até EOF**, com validação de opcode/cache pelo parser anterior. `03-select.py` registrou **zero destinos de salto fora dos limites de instrução** em binding-validation.json. Não se verificou semântica completa da VM/tabela de exceções. A tentativa inicial com 87251/types.py e 90886/__init__.py mostrou enums e módulo vazio, sem elo de controller; o relatório final de decodificação preservado seleciona os três módulos úteis.

Nenhum arquivo fora de camera-binding foi modificado por esta etapa. Nenhuma sessão REA/Ghidra adicional foi aberta, pois a pergunta de construção foi respondida pelos recursos Python estáticos existentes.

## Complemento nativo: cadeia candidata sustentada por acessores

O relatório acima foi ampliado após localizar os bindings nativos. **ClientPlayer.Camera**, e não IPlayer.Camera, é a propriedade qualificada realmente presente na amostra. O bloco em RVA **0x51f8410** declara dono ClientPlayer, tipo ICamera e nome Camera; ponteiro ao nome qualificado em **0x51f8440**. Os callbacks no mesmo registro são:

- **0xd09ec0**: `lea rax,[rdx+0xd88]; ret` (endereço do armazenamento).
- **0xd09ed0**: `mov rax,[rcx+0xd88]; ret` (getter).
- **0xd09ef0**: `mov [rcx+0xd88],rdx; ret` (setter).

Isso sustenta armazenamento de ponteiro **ClientPlayer+0xd88** para a propriedade Camera. Bytes, RVAs e offsets de arquivo estão em native-binding-functions.json; bloco tipado em native-binding-blocks.json.

A única referência RIP validada ao literal **GetGameplay** (RVA **0x5bb9e18**) ocorre no registro de funções **0x3268a60**, instrução **0x3269453**. A mesma sequência instala a rotina **0x3271090** em `[descriptor+8]` em **0x3269463–0x326946a**, com nome em `[descriptor]` e valor 4 em `[descriptor+0x10]`. O valor 4 não teve sua semântica inferida. O callback contém:

```
3271096 mov rax,[module_base+0x80d5980]
327109d mov rcx,[module_base+0x8e455b8]
32710a4 mov rdx,[rax+0x58]
32710a8 call module_base+0x2d829a0
```

A rotina retorna o resultado dessa conversão, salvo quando a checagem subsequente em 0x2a70dc0 retorna não nulo, caso em que retorna zero. A interpretação precisa dessa checagem ainda não foi fechada. A procedência de RDX no callback está provada: **[[module_base+0x80d5980]+0x58]**. Nome do registro e uso do retorno Python sustentam a ligação com GetGameplay, sem execução.

Com IGameplay.Player+0x58 já sustentado em gameplay/GAMEPLAY.md, a cadeia externa **candidata** resultante é:

```
root     = read_ptr(module_base + 0x80d5980)
gameplay = read_ptr(root + 0x58)
player   = read_ptr(gameplay + 0x58)
camera   = read_ptr(player + 0xd88)
```

O último deslocamento exige que Player seja o subobjeto ClientPlayer esperado pelo binding; a reflexão IGameplay.Player declara IComponent, portanto essa transição de tipo concreto **continua sendo requisito de validação**, não fato estabelecido apenas pela cadeia. A variável global raiz não teve sua criação/tipo/lifetime demonstrados nesta sequência. Cada deslocamento acima vem de instrução estática; nenhum foi escolhido por heurística espacial.

O getter de **ICamera.ViewMatrix**, callback **0x93f1a0**, carrega ajuste assinado da célula **0x4f45138**, soma ao argumento RDX e chama indiretamente o ponteiro da célula **0x4f45130**. Logo não é um acesso direto de matriz em ICamera+constante no corpo desse callback. É necessário resolver a inicialização dessas células antes de declarar layout de ViewMatrix.

As lacunas de projeção/viewport principal e alias com CameraProjection continuam abertas. As novas evidências são 04-native-bindings.py a 08-root.py e seus JSONs; os scans de xrefs validam limites de instrução/unwind para as formas suportadas e não constituem busca global de todas as codificações.

### Atualização de leitura das células

O scan08-root.py produziu433 xrefs suportados para80d5980 e1239 para8e455b8. O nome exploratório `GetGameplay_result_type_cell` em native-root-xrefs.json **não é conclusão de tipo**:8e455b8 é objeto global comum ao conversor, criado com40h bytes em2d845b0, e não foi demonstrado como descritor específico de IGameplay. Os JSONs preservam o rótulo do experimento para rastreabilidade. O scan não encontrou store direto MOV[rip],registrador para80d5980 na cobertura; não é prova de imutabilidade ou ausência de outros escritores. A célula raiz está em região virtual sem backing de arquivo.

O valor inicial em disco da célula ViewMatrix4f45130 é VA140964090; ajuste4f45138=0. O thunk964090 retorna camera+41c. Isso já constava da V4 e foi reconferido aqui; native-cells.json/viewmatrix-thunk.json são corroboração, não descoberta independente de novo layout. A cadeia global exata80d5980→58→58→d88 também já era consumida em314c250 da V4; o ganho desta etapa é ligar as parcelas aos nomes GetGameplay/IGameplay.Player/ClientPlayer.Camera e ao caminho Python de controle.
