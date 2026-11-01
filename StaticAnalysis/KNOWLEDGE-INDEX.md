# Base local da investigação

Atualização: 01/11/2026. Esta é uma referência persistente do projeto, não alteração do treinamento de um modelo. A meta continua sendo ESP/aimbot externo funcional; os estados abaixo não a declaram concluída.

## Identidade e limites

- Executável: `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe`.
- SHA-256 fixado: `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`.
- Base preferencial `0x140000000`; RVAs não são endereços observados de processo.
- V2/V3/V4 estão preservadas. Complementos novos ficam em `integration-evidence/`.
- Execução do jogo, acesso ao processo protegido e validação dinâmica não ocorreram nesta integração.

## Conhecimento sustentado e próximo vínculo

| Questão | Evidência disponível | Limite que muda a próxima ação |
|---|---|---|
| Identidade do registro | V4: serial atômico de Skeleton, ator associado e payload ActorComponent separados | Wrap, reset, exclusividade de associação e instâncias reais permanecem abertos |
| Condição da associação | `parent-state/PARENT-STATE.md`: token internado 0x5b resolve IsInWorld | Não é classificador de jogador/NPC |
| Código de gameplay | `assets/script-candidate-index.json`: 9.705 streams sem sobra; `zlib-trailer-probe.json`: mais 130 streams válidos com oito bytes restantes | Um payload excede o limite de entrada; nomes literais do índice não são análise semântica |
| Formato Python | `python-format/PYTHON-FORMAT.md`: CPython 3.14, envelope de oito bytes, 923 code objects de 36 payloads analisados até EOF | Preservar parser próprio; ferramentas pyc da referência REA não demonstram suporte a esse envelope/versão |
| Produtores de componente | `gameplay/python-model-links/`: SimpleModel/WeaponModel chegam à fábrica ActorComponent, com alternativa SkeletonComponent | AvatarModel passa por PoseSenderModel; encadeamento de fábrica e filtros do proprietário ainda precisam ser fechados |
| Posição da entidade | `entity-position/ENTITY-POSITION.md` + `ExternalCore/entity_position.py`: tradução float32 com origem inteira assinada e soma double | Aquisição coerente, identidade dinâmica do IEntity e frame/unidades ainda não observados |
| Câmera | `python-camera/PYTHON-CAMERA.md` e `camera/CAMERA-IDENTITY.md` | Placer/controller, câmera efetiva, bloco CameraProjection e viewport ainda não formam uma cadeia externa completa |

## REA integrado ao fluxo

Referência: [morluto/rea](https://github.com/morluto/rea), checkout local `tools/rea-source`, commit `0281d101307c8884f64d8d31f48e6ca982e3c42a`. A skill de referência é `.agents/skills/reverse-engineer-anything/SKILL.md`, lida no checkout. A CLI instalada no workspace é **rea-agents 6.7.0**. Use `tools/rea.ps1` para reaproveitar o Node existente e os providers portáteis; não foi necessário registrar MCP nem reiniciar o cliente.

O código de `main` e a distribuição npm não têm exatamente o mesmo catálogo: `inspect-native-exports` é descrito no source consultado, mas a CLI instalada rejeitou o comando. Conservar o erro e usar o catálogo realmente disponível; não inferir capacidades do número de versão ou de documentação de outra revisão.

`integration-evidence/rea/doctor-ghidra.json` contém diagnóstico **healthy para o escopo Ghidra**. O agregado `environment_healthy=false` inclui providers não solicitados ausentes, e não contradiz esse resultado. Providers: Ghidra 12.1.4 e JDK 21.0.9+10 em `tools/providers`, com arquivos baixados e hashes conferidos em `provenance.json`. Não houve mudança global de PATH ou de configuração do chat.

Comando observado de REA sobre a amostra:

```powershell
& .\tools\rea.ps1 inspect-pe-resources 'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe' --max-file-bytes 150000000 --json
```

Evidência: **`ev_f7aa275ce425530f1eeec14132fea8034749960bbb92245f42ee803475bade69`**, em `integration-evidence/rea/pe-resources-evidence-expanded.json`. O limite inicial de 64 MiB foi recusado; o pedido corrigido amplia somente o orçamento de leitura para o mesmo arquivo de 141.431.288 bytes. Isso é inspeção de recursos PE, não análise de tipos de gameplay.

## Decompilação focada reutilizável

`integration-evidence/rea/focused-result.json` é resultado **Ghidra direto**, não Evidence do provider REA. O script `ghidra/FocusedDecompile.java`:

1. Confere o SHA do programa importado e a base preferencial.
2. Confere bytes de cada instrução selecionada contra um plano gerado a partir dos CFGs auditados.
3. Desmonta somente as faixas selecionadas e decompila em banco privado com `-noanalysis`.
4. Preserva pseudocódigo e diagnósticos, sem executar o alvo.

As duas primeiras funções (`0x1408977b0`, `0x1419c0100`) passaram, cobrindo 474 registros de instrução. O pseudocódigo da primeira corrobora a regra de anchors do módulo implementado. A terceira (`0x142d85130`, CreateObject) foi decompilada reaproveitando o banco e conferindo mais 63 registros. Seu fluxo passa pela fábrica `0x1404fa480` e pela conversão nativo/Python `0x142d82d90`; a resolução concreta de cada nome continua exigindo seguir os produtores de metadados.

O banco reutilizável está em `integration-evidence/rea/ghidra-project/BloodStrikeFocused`. Para outro alvo de função, gere um **novo** plano/output com `prepare_focused_plan.py --function RVA:label --output arquivo.json`, depois processe o programa existente com `-process BloodStrike.exe -noanalysis`. Não reimporte o executável sem necessidade. O primeiro importador também inspecionou DLLs locais de dependência para símbolos; elas não foram executadas e não são evidência de instâncias do jogo.

Pseudocódigo tem tipos inferidos e corpos sem expansão de callees. Ele complementa os bytes, não substitui validação de indireções, aliases, chamadas Python ou execução.

## Implementação e validação atuais

Na integração de 22/10, `ExternalCore/entity_position.py` tinha oito testes offline aprovados, preservados em `entity-position/offline-tests.txt`.

Em 26/10 foi implementado o coletor `ExternalCore/registry.py`, com memória sparse/offline e leitor Win32, gate de build em disco, resolução RTTI conservadora e duas passagens comparadas. `screenpoint.py` implementa a projeção do helper nativo 0x275db0. **40 testes passaram no Windows/Python 3.12.14, incluindo quatro integrações Win32 com processos filhos próprios; zero acesso ao processo protegido.** O relatório fonte é `reports/tests/summary.json`, JUnit ao lado. CI configurada em `.github/workflows/test.yml`, sem run remoto afirmado.

Novas evidências: `camera-binding/CAMERA-BINDING.md` fecha a construção do controller a partir da instância Camera e sua ControlledCamera=GetGameplay().Player.Camera. `camera-binding/SCREENPOINT-CONTRACT.md` fecha nome→binding→helper→campos e arredondamento de tela. `actor-classification/README.md` fecha a herança AvatarModel→PoseSenderModel→SimpleModel e distingue consultas de owner, sem convertê-las em offset nativo de jogador.

Bloqueios de integração persistem: frame dos anchors versus float3 da câmera, tipo concreto Player/viewport final e classificação externa dos alvos. Overlay e aimbot ainda não implementados. Duas leituras iguais não fornecem atomicidade, exclusão de ABA ou geração de vida. O índice não declara cheat pronto. Uso e limites atuais em `../IMPLEMENTACAO-E-TESTES.md`.

## V5 — integração de 01/11/2026

O parágrafo anterior descreve o marco de 26/10. A implementação atual está em `../INTEGRACAO-V5.md`: câmera tipada por RTTI, cena, overlay GDI, mira com suavização/calibração, adaptador SendInput e loop explícito de observação. **73 testes passaram**, incluindo nove nativos em processos/janelas próprios. Não houve leitura do processo protegido nem eventos de mouse no sistema.

`gameplay-classifier-v5/` demonstra class-tag PlayerCombatAvatar, o owner passado ao AvatarModel e os stores `IEntity.owner`/`.instance`. Armas também carregam owner jogador; o MRO AvatarModel é discriminador adicional. `python-owner-v5/` fornece o layout 3.14 fixado e corroborado; `python_owner.py` implementa observação guardada da associação e dados. Resultado positivo é candidato `player`, sem equipe, vida, visibilidade ou jogador local conhecidos; nunca vira `opponent` automaticamente. Previews/modelo principal ainda não estão eliminados.

Correções: tupla CPython3.14 usa itens em +0x20, não +0x18. Leitores antigos de `STORE_ATTR` em actor-classification e python-model-links aplicavam shift incorreto; a errata V5 limita seus nomes derivados, preservando bytes/hashes/IDs. Novas conclusões usam o índice direto. Não reusar interpretações legadas de stores sem essa correção.

`runtime-v5/verify_delivery.py` confere amostra em disco, identidades/bytes novos, fontes vinculados à suíte e manifesto V4. `reports/tests-v5/summary.json` é o resultado atual; o relatório de 40 testes em `reports/tests/` permanece histórico. A validação dinâmica do jogo e os filtros de adversário continuam necessários para concluir a meta.

## V6 — owner, estado e identidade de predicado

O estado atual está em `../INTEGRACAO-V6.md` e `../reports/tests-v6/summary.json`: **108 testes PASS**, nove integrações nativas próprias, zero acesso ao processo protegido/entrada física. As descrições V5 acima são históricas. O resultado V5 continua vinculado aos fontes arquivados na V5, não certifica alterações V6.

A suposição de owner direto foi corrigida: AvatarModel recebe `self.area`. `native-properties-v6/` demonstra proxy area → host Python e associação reversa. O core exige também os links armazenados host.model/instance.model. `managed-models/` fornece o layout 3.14 de managed/inline/split dictionaries, sem materialização ou getters remotos. Isso melhora o candidato player; não prova ausência de previews.

`local-player-v6/` fecha `_PyRuntime`/interpretadores/sys.modules/módulo exato e dicionário. `python_runtime.py` procura genv.player com identidade reversa; recusa ambiguidade/aliases/replay distinto. `native_properties.py` descobre nomes/descritores por classe e lê int64/double/tags mistas numéricas. Não existe índice universal de HP/equipe nem fallback numérico em caso de falha.

`combat-state-v6/` demonstra regras específicas de inimigo e allowlists de CombatState. HP não determina vivo/morto. O enum tem import e âncora nos defaults, mas tipo/integer encoding seguem desconhecidos. `predicate-code-v6/` e `ExternalCore/predicate.py` comparam o corpo base de IsEnemy, incluindo operandos, normalização de especializações e checagens de mutação. A CLI `predicate` analisa uma captura gravada; não chama o alvo. Corpo igual não estabelece método ativo ou comportamento dos getters.

`native-properties-v6/attribute-dispatch/` separa resolução Python de dados NumericMap: lookup genérico do host precede fallback; atributos/descritores podem sombrear o mapa, e bool/length do tipo efetivo afetam verdade do objeto. Essa fronteira impede promover facção bruta para opponent automaticamente. `runtime-v6/verify_delivery.py` reconfere os bytes/MPKs selecionados, manifestos anteriores, spec gerada e fontes da suíte. Não atribui geração de vida a endereço ou serial e não conclui a meta do cheat.

## V7 — estado atual

Relatório atual: `../INTEGRACAO-V7.md`; suíte: `../reports/tests-v7/summary.json`, **133 PASS**, nove testes nativos próprios. V6 e seu ZIP continuam preservados. O processo protegido e entrada física não foram usados nesta etapa.

`dispatch-v7/` demonstra binding/wrapper/hook, dicionários de tipos estáticos por interpretador e aliases do cache. `python_dispatch.py` implementa precedência e aceita apenas o corpo base de IsEnemy após resolver o método real em `genv.space.game_logic`. Operandos int efetivos, slots de verdade e ausência de callbacks não sustentados são exigidos. Relação positiva pode gerar opponent; overrides não são ignorados.

`state-v7/` encontra a definição em MPK141076 e metaclass em66389: ALIVE0, DYING1, DEAD2, GHOST3, NONE4, SPIRIT5. `life_state.py` confere o enum carregado no mesmo interpretador e possíveis sombras de metaclasse antes de usar combat_state efetivo. HP não decide vida.

`camera-v7/` fecha a rota independente `[base+80f3840]→state+8→client+18→viewport+50`, com tipo e aliases. `render_camera.py` adquire projeção Aurora/Perspective e compara modo/dimensões/cópia de origem. O loop watch exige a entrada de render. Convenções, jitter/escala, shader final e pixels apresentados seguem desconhecidos; ScreenPoint continua candidato. A suíte completa demonstra planejamento com perfil de teste explícito, sem enviar input. `runtime-v7/verify_delivery.py` vincula fontes/testes, bytes, MPKs e manifestos. A meta do cheat em partida continua aberta.
