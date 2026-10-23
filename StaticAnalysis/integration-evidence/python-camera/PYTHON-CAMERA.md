# Três módulos de câmera: seleção, posse e mira

Amostra estática: índices **50901** (`engine_placer.py`), **75597** (`base_placer.py`) e **78462** (`aim_placer.py`) de `script-candidate-index.json`. Hashes comprimidos/decodificados reconferidos ao reler somente essas três entradas. Não houve execução ou importação do bytecode alvo. O parser/decoder corrigido de `python-format` foi reutilizado sem alterá-lo; V2/V3/V4 preservadas.

## Conclusão

Os três módulos implementam **placers e blending controlados por um master recebido**, não a seleção da câmera de gameplay ou aquisição da câmera de renderização. A evidência de instruções mostra criação de `AimPlacer`, cópia de configuração para esse objeto e entrega a `master.controller.BlendInPlacer`. Não há aqui uma atribuição que identifique `master.controller` como o `CameraController` nativo, nem uma seleção `GetGameplay`/`Camera`/`MainCamera`.

Há evidência nativa independente de que propriedades de **CameraController.ControlledCamera/AffiliatedCamera são declaradas ICamera**, e `VirtualCtrlCamera` é declarada VirtualCamera. Isso estabelece uma distinção refletida entre espécies de objetos, mas não fecha o alias com o master genérico desses módulos.

**39 code objects** foram consumidos até EOF (17/16/6 por módulo), com validação de opcodes e inline caches 3.14. Todos os destinos dos saltos decodificados caem em limites de instrução. Isso não equivale a validação semântica completa da VM ou das tabelas de exceção.

Os offsets abaixo são **offsets em bytes dentro de `co_code` de cada função**, não RVAs nativos ou offsets de campos. `marshal_offset` identifica o code object no payload descomprimido. Evidência integral em `camera-modules-static.json` e `camera-disassembly.txt`; recorte em `camera-selected-evidence.json`.

## 1. Posse recebida e escolha de tipo de placer

`BasePlacer.__init__` (índice 75597, marshal 312; locais `self, master`) executa em **2** `LOAD_FAST_BORROW_LOAD_FAST_BORROW 0x10`, resolvido como **master, self**, e em **4** `STORE_ATTR master`. Assim, a posse local é `self.master = master`, sem factory de câmera nessa função. `BasePlacer.target`, offsets **2/4/24/44**, carrega `self → master → target` e retorna o resultado; `debug_enabled` faz o análogo para `master.debug`.

`BasePlacer.GetAllPlacerTypes` mantém um cache `BasePlacer.Placers`. Se esse cache for falso, offset **44** não toma o salto a 208 e percorre subclasses: `stack.pop(0)` (80–104), armazena `placers[cls.__name__]=cls` (114–138) e estende com `cls.__subclasses__()` (142–194). `GetPlacerType` chama esse inventário em **32** e `.get(name, None)` em **64**. Portanto, a seleção mostrada é de **classe de placer por nome**, dependente das subclasses carregadas; não de câmera ativa do renderizador.

A identidade do argumento master e a criação do seu controller estão fora desses três módulos. `BasePlacer.OnActive` levanta `NotImplementedError`; vários métodos base são no-ops. Nenhum deles deve ser interpretado como rotina nativa de câmera só pelo namespace Python.

## 2. Criação e entrega do objeto de mira

`AimPlacer.OnActive` (índice 78462, marshal 1263; locais `self, info, target_pos_offset, length, need_blender, __class__`) primeiro chama o `super(...).OnActive(info)` em **32**. A resolução esperada pelo import/classe é EnginePlacer, mas globals e classes Python podem ser substituídos dinamicamente.

Se info for falso, **52** salta a **346**, pulando os overrides de offsets/distância. No ramo com info:

- **90–192** chama `info.get('right_offset',0)`, `get('upper_offset',0)`, `get('back_offset',0)` e `MType.Vector3(...)`; **200** guarda local `target_pos_offset`.
- **212** testa a verdade desse objeto. No ramo verdadeiro, fused load em **218** carrega `target_pos_offset,self`; **220** grava `self.TargetPosOffset`. O resultado de truthiness do tipo Vector3 não foi executado ou presumido.
- **230–262** lê `info.get('target_distance')` para local `length`; **274** pula a 346 se falso. Caso verdadeiro, **280** carrega `length,self`, **282** carrega `self.AimDirection` e **302** grava a propriedade `length` desse vetor; **312–336** copia `self.AimDirection` para `self.Direction`.

Na sequência comum **346–390**, carrega `MObject.CreateObject`, passa a string **`AimPlacer`**, chama em **380** e grava o resultado em `self.placer` em **390**. Em **400–424**, grava `self.placer.ManualAdjust=True`. Em **436/456**, chama `self.RefreshConfig()`.

Depois obtém `need_blender = info and info.get('need_blender')` (466–518); chama `self.BlenderInFinished()` em **542**; apenas no ramo verdadeiro de `need_blender` chama `CreateBlender(blend_type=self.blend_type)` em **618**. Finalmente:

| Offsets | Fluxo de dados |
|---|---|
| 628–670 | carrega `self.master.controller.BlendInPlacer` |
| 690–714 | carrega `self.placer` e `self.blender` |
| **734** | chama o método com esses dois argumentos |
| 744–768 | grava `self.master.enableCollider=True` |

Essa é uma entrega concreta de dois objetos ao controller por método Python/binding. **Não é uma chamada de projeção nem leitura de matriz.** O retorno de CreateObject pode ser wrapper nativo conforme o ambiente, mas o tipo dinâmico não foi inspecionado em runtime.

## 3. Copiar configuração não equivale a ligar campos C++

`EnginePlacer.__init__` guarda placer/blender como None, is_actived=False e configura parâmetros de blending. `StartExposeProperties` registra as chaves de `self.__dict__`; `FinishExposeProperties` calcula a diferença de chaves e salva `expose_properties`. No construtor de AimPlacer, os campos são criados entre essas duas chamadas.

`EnginePlacer.RefreshConfig` (marshal 3255; locais `self,config,key,value`) retorna cedo se `self.placer` for falso: salto **32→42**, retorno no outro ramo **38–40**. Se config for falso (**52** não toma salto para 146), monta um dicionário a partir das chaves expostas e de `self.__dict__`. No loop final:

- **178** FOR_ITER sai em 236;
- **182/186** desempacota `key,value` em locais;
- **188** carrega global `setattr`;
- **198–220** carrega `self.placer,key,value`;
- **222** chama `setattr(placer,key,value)`;
- **232** volta ao loop em 178.

Logo, nomes como Direction/Fov/TargetPosOffset são enviados como atributos a um objeto retornado pela factory. O layout dos atributos Python não determina deslocamentos nativos. Um config fornecido pelo caller pode conter nomes fora do conjunto padrão.

O construtor de AimPlacer atribui defaults como TargetPosOffset=Vector3(0,1.5,2), AimDirection=Vector3(0,-1,6.5), Direction=esse vetor, Fov=60 e limites de pitch calculados com math.pi. São valores de configuração observados em LOAD/CALL/STORE; não fixam unidades espaciais, FOV horizontal/vertical, projeção final ou tamanho de viewport.

## 4. Alvo e direção de mira

`EnginePlacer.SetFocusTarget` (marshal 2674; locais `self,target`) testa sucessivamente placer, `placer.IsValid()`, master e master.collider. Os ramos negativos convergem para retorno **194–196**; a última condição positiva salta **188→198**. Depois seleciona `target.model` ou None (198–238) e grava **`self.placer.Target` em 262**. Repete essa seleção e grava **`self.master.collider.Target` em 356**. O mesmo argumento target é usado, mas os dois resultados de `target.model` são acessos dinâmicos separados.

`AimPlacer.SetFocusTarget` (marshal 2594; locais `self,target,direction,__class__`) chama o super em **32**, sem usar seu retorno como sucesso/fracasso. Se target for falso, **52→294** retorna. Caso verdadeiro, **90–154** calcula `MType.Vector3(*formula.YawToVector(target.yaw))` e guarda local direction em **156**. Em **158–202**, copia o comprimento atual de `self.AimDirection` para `direction.length`; **212/214** grava `self.AimDirection=direction`; **224–248** grava `self.Direction=self.AimDirection`; **260/280** chama RefreshConfig.

Portanto, o ajuste da direção pode ocorrer após um retorno cedo do método base: a subclasse só condiciona esse bloco à verdade de target. A semântica interna de YawToVector e os eixos/unidades do vetor não foram analisados aqui.

`AimPlacer.TurnView` (marshal 3141; locais `self,diffx,diffy,shoot_adsorb`) grava `self.placer.ManualAdjust=True` em **26** e chama **`self.placer.Rotate(diffx,diffy)` em 80**, com fused load dos locais 1 e 2 em **78**. `shoot_adsorb` não é carregado nesse corpo. O método não calcula uma posição de pixel ou uma matriz de renderização.

## 5. Blending e diferenças em relação a render

`EnginePlacer.CreateBlender` libera o blender existente via `self.master.controller.Release(blender)` em **122** se o ramo de truthiness o permitir. Cria `MObject.CreateObject('LerpBlender')` em **166**, guarda em `self.blender` em **176**, atribui BlendTime/BlendType/DirectTransit e associa callback de evento `RemovedFromTree` em **432**. Os argumentos blendTime/blend_type são escolhidos por truthiness (saltos 196 e 270), não simplesmente por comparação com None.

`BlenderInFinished` tenta Release em **126** se blender for verdadeiro e sempre grava `self.blender=None` em **140**. `OnDeactive` também libera o blender e desmarca is_actived; não há neste corpo Release ou destruição de self.placer. Não se extrapola a política global de lifetime a partir desses caminhos locais.

A mira demonstrada é **um nó de controle/posicionamento configurável submetido a uma árvore de blending**. A câmera de renderização final depende de código que aplica o controller a câmeras e escolhe a câmera/viewport da passagem. Esses elos não estão presentes nos três módulos. O caminho nativo V4 que constrói PerspectiveCamera temporária 2048×2048 para DecalCameraData não foi equiparado à saída desse placer.

## 6. Tipos nativos declarados: ponte parcial independente

Uma leitura adicional das strings e blocos de reflexão do PE, sem processo, encontrou:

| Propriedade qualificada | Ponteiro ao nome qualificado | Tipo declarado no mesmo bloco |
|---|---:|---|
| CameraController.ControlledCamera | RVA `0x55ef870` | **ICamera**, apontado em `0x55ef850` |
| CameraController.AffiliatedCamera | `0x55ef980` | **ICamera**, em `0x55ef960` |
| CameraController.VirtualCtrlCamera | `0x55efa90` | **VirtualCamera**, em `0x55efa70` |
| AimPlacer.Target | `0x55f9460` | **IEntity**, em `0x55f9440` |
| AimPlacer.TargetTransform | `0x55f9570` | **Matrix4x3**, em `0x55f9550` |
| AimPlacer.Fov | `0x55f8250` | **float**, em `0x55f8230` |

`native-property-blocks.json` guarda bytes e QWORDs dos blocos, não apenas strings. Os blocos de ControlledCamera/AffiliatedCamera possuem wrappers getter `0x1d87570`/`0x1d87a90`, cuja desassemblagem em `native-wrapper-code.json` mostra consulta a células de membro-função e retorno desreferenciado. Esses fatos sustentam propriedades de tipo câmera declaradas pelo sistema nativo.

**Ponte que falta:** os módulos não constroem ou tipam `master.controller`, não acessam essas três propriedades e não contêm retorno de ControlledCamera que possa ser seguido até o placer. Portanto, o nome de método `BlendInPlacer` e a correspondência dos nomes AimPlacer são coerentes com a API nativa, mas não bastam para provar identidade de objetos ou seleção da câmera renderizada. Nenhum offset C++ foi derivado de atributos Python.

## 7. Cobertura e lacunas

`camera-validation.json` registra ausência exata em co_names desses três módulos de GetGameplay, Camera, MainCamera, ICamera, Transform, ViewMatrix, Project, ProjectInner, CameraMatrix, GetScreenSize, SetScreenSize e WorldPosition. Não é uma afirmação global sobre o jogo: setattr/configuração, classes, globals e métodos dinâmicos podem introduzir acessos indiretos.

Não foi recuperada aqui chamada de projeção, divisão por W, clipping, viewport, escrita em ICamera.Transform/ViewMatrix ou uso de MainCamera. TargetTransform aparece somente na evidência nativa adicional, não como acesso de instrução desses três módulos. O controller/gerenciador que fornece master, a aplicação do blending à câmera e a escolha da câmera final são lacunas específicas para uma próxima etapa.

Reprodução: scripts 01–05 nesta pasta. O decoder de nomes adiciona resolução de LOAD_FAST_BORROW e do fused LOAD_FAST_BORROW_LOAD_FAST_BORROW; os operandos de nomes de LOAD_ATTR/LOAD_GLOBAL e LOAD_SUPER_ATTR têm seus bits de flags retirados. Saltos usam offsets após caches. Nenhuma função de code object foi executada. Os hashes/fontes do parser 3.14 permanecem no diretório python-format original.
