# Integração V7 — 01/11/2026

A V7 liga o classificador ao método de relação efetivamente resolvido, acrescenta o esquema comprovado de `CombatState` e adquire a câmera nativa usada como entrada do `MainRenderViewport`. O fluxo completo foi exercitado com estruturas de teste: registro → modelo → adversário → ALIVE → câmera do viewport → projeção candidata → planejamento de mira. **133 testes passaram**, incluindo nove integrações nativas em processos/janelas próprios.

Isso amplia a implementação externa; ainda não demonstra funcionamento no Blood Strike em execução. O escopo desta etapa permaneceu em arquivos e processos próprios, conforme a restrição anterior. A amostra e os recursos não foram executados, o processo protegido não foi acessado e nenhum movimento de mouse foi enviado. Não existe certificação NetEase ou execução de CI remota afirmada.

## V6 × V7

| Pergunta | V6 | V7 | Limite atual |
|---|---|---|---|
| Qual regra identifica adversários? | Verificava um corpo Python fornecido por endereço | Resolve `genv.space.game_logic.IsEnemy`, respeita MRO, precedência e binding; aceita o corpo base conhecido | Overrides e getters não sustentados ficam desconhecidos |
| O mapa numérico é o atributo Python? | Valores brutos e advertência sobre sombras | Confere lookup efetivo, descritores, atributos de instância/classe, aliases e slots de verdade | Fallback Python arbitrário e execução de descritores não são emulados |
| Qual estado significa ALIVE? | Enum e valor desconhecidos | Definição e metaclass demonstram ALIVE=0, DYING=1 e demais estados; namespace carregado e metaclasse são conferidos | Exige que `combat_state` seja obtido por um caminho efetivo suportado |
| Qual câmera chega ao viewport? | `Player.Camera` candidata | Rota independente tipada até o objeto de câmera associado ao MainRenderViewport | Convenção de matriz, jitter, escala e pixels apresentados ainda abertos |
| O pipeline seleciona um alvo? | Candidatos player não viravam opponent automaticamente | O classificador padrão pode produzir opponent/ALIVE e plano, quando todos os gates passam | Visibilidade é desconhecida e a calibração do jogo não foi observada |
| Testes | 108 aprovados | 133 aprovados, zero falhas/erros/skips | Buffers controlados não são uma captura de partida |

## Adversários: resolução e operandos

`ExternalCore/python_dispatch.py` resolve o atributo pela classe efetiva e sua MRO, examina descritores antes do dicionário da instância e recusa callbacks não sustentados. Ele aceita o getter genérico, o getter nativo de entity e o hook CPython quando o `__getattribute__` escolhido é o wrapper nativo comprovado. Um retorno positivo por esse caminho não executa `__getattr__`; um miss que exigiria fallback Python permanece desconhecido.

O método precisa ser uma função de classe com binding suportado. O primeiro override encontrado não é ignorado para buscar um ancestral conhecido. A função selecionada passa pelo verificador V6 de corpo, assinatura, nomes, constantes e demais operandos. O caminho atual aceita `IGameLogicBase.IsEnemy`; não estende essa regra aos modos com outros corpos.

O atributo `faction` pode vir da instância, da classe ou de armazenamento nativo numérico. Um descritor, um tipo de operando incompatível ou um hook customizado impede a decisão. No caminho nativo, são exigidos os dois aliases do cache: `HostBridge+0x18 == MapPy` e `HostBridge+0x20 == [MapPy+0x20]`, além da associação reversa com a area. O setter nativo demonstra essas atribuições; também possui um ramo com mapa nulo que pode deixar cache anterior, portanto os aliases são conferidos na observação.

Tipos builtin estáticos têm dicionários por interpretador. O leitor agora segue esse armazenamento com índice limitado, identidade de tipo e estado ready; não os trata como dicionários vazios. A verdade dos operandos usa os slots efetivos bool/length: callbacks não reconhecidos impedem avaliação passiva. Para inteiros de facção efetivos, a decisão reproduz a ordem de identidade, verdade, facções negativas e desigualdade do corpo verificado.

Uma relação positiva pode promover o candidato a `opponent`. Uma relação negativa conserva `player`; ela não é rotulada automaticamente como teammate. Função e regra observadas são expostas em `classification.facts`. As duas passagens de metadados abrangem esses dados. Igualdade não fornece atomicidade ou geração de vida.

Evidências principais: `integration-evidence/dispatch-v7/PASSIVE-DISPATCH.md`, `PASSIVE-DISPATCH-CONTRACT.json`, construtor/cache setter, helpers de dicionário e wrappers. O corpo aceito continua identificado por `predicate-code-v6/`.

## Estado de vida: definição encontrada

O MPK **141076**, `gshare/consts.py`, define diretamente:

| Estado | Inteiro |
|---|---:|
| ALIVE | 0 |
| DYING | 1 |
| DEAD | 2 |
| GHOST | 3 |
| NONE | 4 |
| SPIRIT | 5 |

O MPK **66389**, `gshare/utils.py`, fornece o enum customizado. Seu metaclass constrói os mapas de nomes/valores e conserva o namespace entregue a `type.__new__`. Os valores não foram inferidos de HP, de defaults de armazenamento ou de enums de outro jogo.

`life_state.py` procura `gshare.consts` no mesmo interpretador do contexto local, confere os seis inteiros exatos e o módulo da classe. Exige o getter canônico da metaclasse e recusa sombras no namespace da metaclasse. Só então associa um `combat_state` efetivo suportado ao nome. Um valor fora do esquema continua desconhecido.

`Classification.alive` é verdadeiro para ALIVE e falso para os demais membros comprovados. O nome completo continua nos fatos: DYING não é confundido com DEAD. O filtro padrão de `AssistAim.SelectTarget` permite ALIVE; o caller Juren Fly Slash admite ALIVE e DYING. A implementação de seleção deste projeto conserva o critério ALIVE; não generaliza a exceção do Juren.

O HP bruto continua independente. Um teste cobre `server_hp=0` e `combat_state=ALIVE`: o resultado de vida segue o estado efetivo, não uma regra inventada de HP. Evidência: `integration-evidence/state-v7/04-combatstate-numeric-contract.json`, definição, criação do enum e consumidores V6 preservados.

## Câmera de entrada do render

`render_camera.py` implementa esta rota, vinculada à amostra:

```text
state    = [module_base + 0x80f3840]
client   = [state + 0x08]       SceneViewportClient
viewport = [client + 0x18]      MainRenderViewport
camera   = [viewport + 0x50]

Exigir [viewport + 0x740] == client
Exigir camera == client + 0x80
```

Vptrs exatos e deslocamento zero foram corroborados pelos construtores e RTTI. O código lê dimensões do viewport e distingue AuroraCamera, PerspectiveCamera e Orthographic3dCamera. Para Aurora/Perspective, lê os 64 bytes de projeção cujos getters foram demonstrados. Para ortográfica, o campo de projeção fica sem valor: seu getter calcula a saída e não foi encontrado armazenamento fixo equivalente.

A atualização de `SceneViewportClient` copia dados de `Player.Camera` e configura esse objeto separado. Na captura integrada são comparados modo, dimensões e a cópia de 48 bytes da visão em `client+0xee0`. As estruturas da câmera de origem e da câmera nativa permanecem distintas. Ponteiros, aliases, vptrs, dimensões, projeção e cópia de origem são comparados antes/depois da coleta do registro.

O loop `watch` agora exige essa entrada de render. A CLI offline aceita `scene --require-render-input`; sem a opção, uma captura pode conservar a câmera candidata, com `render_camera_error` explícito. Esse modo permissivo de leitura não marca a projeção como validada.

**A matriz obtida é de projeção, não uma view-projection combinada demonstrada.** A ordem de multiplicação, faixa de profundidade, jitter, escalas de resolução, vínculo com o bloco final do shader e mapeamento a pixels apresentados continuam abertos. `Scene.final_viewport_validated` e `RenderCamera.presented_pixels_validated` continuam falsos. O helper ScreenPoint anterior permanece a projeção candidata usada pelo pipeline; esta etapa não prova sua equivalência aos pixels finais.

A atualização pode retornar sem atualizar a câmera quando a origem falta. Leituras iguais e cópia coincidente não provam agendamento, frescor ou ausência de substituição posterior. Evidências: `integration-evidence/camera-v7/effective-camera-contract.json` e `discriminating-native-evidence.json`. Os catálogos grandes dessa pasta são exploração; não são prova de equivalência por si mesmos. As regiões unwind encadeadas foram tratadas explicitamente.

## Testes e reprodução

Python 3.12+ x64, a partir da raiz do projeto:

```powershell
python tools/run_tests.py --output-dir reports/tests-v7
python StaticAnalysis/integration-evidence/runtime-v7/verify_delivery.py
python StaticAnalysis/integration-evidence/runtime-v7/make_example.py
python -m ExternalCore scene reports/examples-v7/memory.json --require-render-input --output quadro.json --svg quadro.svg
```

A suíte usa biblioteca padrão e processos/janelas próprios. O verificador estático requer a instalação original, recursos e manifestos preservados. O gerador de exemplo grava buffers sintéticos com procedência explícita, executa a CLI real e produz `plan.json` com um plano, sem despacho de entrada.

O teste completo usa `require_visible=False` como política explícita e contagens/pixel de teste; ele não inventa visibilidade ou calibração do jogo. Com o perfil padrão, a visibilidade desconhecida impede seleção. O loop `watch` continua sem despacho de mira.

Resultados registrados: **133 testes**, nove integrações nativas próprias, 54 fontes/testes vinculados por SHA-256. Verificação em disco: **671 payloads MPK**, 344.825 registros de bytes incluindo repetições, 211.289 pares distintos de RVA/tamanho e 98 artefatos selados V4 intactos. Os números incluem evidências reutilizadas e decodes exploratórios; não representam cobertura semântica integral. O SHA-256 do executável permanece `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`.

V6 e seu pacote permanecem históricos e preservados. Não se rerrotulou a suíte V6 como resultado dos fontes V7.

## O que falta para afirmar funcionamento no jogo

A relação base e o estado de vida agora possuem caminhos implementados e testados com os metadados requeridos. Sua presença e seleção nas instâncias reais ainda precisam ser observadas. Modos com outros predicados continuam recusados até haver implementação correspondente.

A entrada nativa do viewport está ligada ao pipeline, mas a equivalência da projeção com a tela continua sem demonstração. Também faltam observação de visibilidade, calibração de entrada, transições de criação/destruição em execução e confirmação de gerações de vida. Nenhum endereço/serial foi tratado como garantia de mesma instância entre frames.

O próximo trabalho discriminante é seguir os consumidores da matriz do viewport até a transformação de tela e observar uma execução controlada compatível com o escopo autorizado. Até isso ocorrer, a entrega é implementação externa com evidências estáticas e testes próprios; não é um cheat validado em partida.
