# Base local da investigação

Atualização: 22/10/2026. Esta é uma referência persistente do projeto, não alteração do treinamento de um modelo. A meta continua sendo ESP/aimbot externo funcional; os estados abaixo não a declaram concluída.

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

`ExternalCore/entity_position.py` está implementado. Oito testes de snapshots sintéticos passaram e o stdout está em `entity-position/offline-tests.txt`. Cobrem float32 antes da soma double, valores assinados/extremos, sentinela coletiva e mista, limites de buffer e input mutável. **Zero testes dinâmicos; ESP e aimbot ainda não implementados/validados como aplicação completa.**
