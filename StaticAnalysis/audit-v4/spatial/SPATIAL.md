# V4 — evidência espacial estática

Amostra: `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe`. SHA-256 conferido ao carregar cada script: `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Base preferencial `0x140000000`. Todos os endereços abreviados são RVAs. Apenas leitura do PE como dados, sem carregar/executar o jogo ou acessar processos. Nenhum offset externo foi empregado como prova.

## Resultado sustentado

Há uma propriedade refletida **IEntity.Transform**, declarada **Matrix4x3**, e uma propriedade **ICamera.ViewMatrix**, também **Matrix4x3**. As duas se ligam por ponteiros de dados a wrappers e getters concretos. O resultado não demonstra uma propriedade Position de IEntity, nem uma matriz de projeção ou rotina world-to-screen de ICamera.

| Ligação | IEntity.Transform | ICamera.ViewMatrix |
|---|---|---|
| String qualificada | `0x4f5fe60` | `0x4f45038` |
| Registro contendo tipo/nome/nome qualificado | `0x4f60590` | `0x4f43b10` |
| Ponteiro ao nome qualificado | `0x4f605b0` | `0x4f43b30` |
| Ponteiro ao wrapper | `0x4f605d0` → `0x954ad0` | `0x4f43b50` → `0x93f1a0` |
| Célula do membro-função no arquivo | `0x4f601c0` → `0x95e880` | `0x4f45130` → `0x964090` |
| Ajuste assinado do objeto | DWORD `0` em `0x4f601c8` | DWORD `0` em `0x4f45138` |
| Getter concreto e bytes | `0x95e880`: `48 8d 41 58 c3` | `0x964090`: `48 8d 81 1c 04 00 00 c3` |
| Efeito concreto | retorna `RCX+0x58` | retorna `RCX+0x41c` |

Em ambos os registros, a string `Matrix4x3` é apontada pelo primeiro QWORD; o nome simples está em +0x10; o nome qualificado em +0x20; o wrapper em +0x40. Esses offsets são relativos aos registros de metadados, não a objetos de gameplay. `data-blocks.json` contém os blocos completos, bytes, offsets de arquivo e valores QWORD, evitando confundir flags e comprimentos com ponteiros.

O wrapper de Transform tem CFG linear: reserva stack em `0x954ad0`; em `0x954ad4` lê o ajuste de `0x4f601c8`; soma ao segundo argumento RDX em `0x954adb`; lê o ponteiro de `0x4f601c0` em `0x954ade`; chama RAX em `0x954ae5`; restaura stack e retorna. O de ViewMatrix repete o padrão em `0x93f1a0`–`0x93f1bc`, com chamada indireta em `0x93f1b5`. Os getters concretos só calculam endereço e retornam; não fazem cópia ou transformação de coordenadas. `selected-code.json` preserva todas as instruções e bytes.

A tabela adicional de nome simples Transform em `0x4f50350` guarda diretamente `0x95e880` em `0x4f50368`; a de ViewMatrix em `0x4f76d00` guarda diretamente `0x964090` em `0x4f76d18`. Isso corrobora as ligações, mas não foi usado para atribuir dono sem a cadeia dos nomes qualificados. A varredura de instruções CALL E8 para esses dois getters, validada dentro de funções unwind, encontrou zero chamadas diretas; os caminhos comprovados são indiretos pelos dados.

## Limites para coordenadas e câmera

- `Transform` está rotulado como Matrix4x3; o getter só prova o endereço do armazenamento relativo ao argumento ajustado de IEntity. Não prova que seja transformação mundial, local, pós-anchor, de renderização ou a mesma transformação de um ActorComponent. Não foi atribuída uma posição aos últimos três floats por convenção.
- `ViewMatrix` não equivale a matriz de projeção. Não há multiplicação, divisão por W, aplicação de viewport ou clipping nos getters demonstrados. Não estão provados layout linha/coluna, handedness, unidade, eixo vertical, reversão de profundidade, limites de tela nem fórmula de world-to-screen.
- O valor estático de uma célula de membro-função é evidência do PE em disco. Não demonstra que não exista substituição durante inicialização ou em runtime. ASLR exige relocação; as VAs preferenciais presentes no bloco não são endereços observados de processo.
- Não se demonstrou seleção da câmera ativa, ligação a jogador local, câmera de mira, espectador, câmera virtual, interpolação ou jitter. A existência de nomes refletidos como `ICamera.VirtualCameraManager`, `ICamera.UseAuroraCamera` e `ICamera.IsOrthographic` não resolve essas diferenças.
- Não foi produzida uma cadeia de leitura externa completa: faltam a aquisição/identidade/lifetime da câmera relevante e uma projeção vinculada a ela, além da semântica espacial do Transform.

## Buscas negativas e falsos atalhos

`negative-string-scan.json` registra contagem zero, em ASCII e UTF-16LE sobre o arquivo inteiro, para `IEntity.Position`, `IEntity.WorldPosition`, `IEntity.WorldTransform`, `ICamera.Project`, `ICamera.ProjectInner`, `ICamera.CameraMatrix`, `ProjectInner` e `CameraMatrix`. Isso limita a abordagem por nomes literais; não prova inexistência dessas operações em código sem strings.

Existe `WorldPosition` em `0x4e90ac0`, mas a busca por nomes qualificados não o ligou a IEntity. Também aparecem `BoardComponent.WorldPosition` em `0x520ad70`, nomes de física e `GetBoneWorldTransform`, que não foram promovidos a propriedades de IEntity. Existem `CameraProjection` em `0x55aef10` e `GetMainCameraViewProjection` em `0x5ba6f28`, sem cadeia de ponteiros/CFG até ICamera demonstrada nesta análise. Nenhum deles sustenta um Project/ProjectInner presumido.

A pista `globality.live/case-bloodstrike` permanece externa e sem correspondência comprovada de build. Os nomes procurados dessa pista não substituem os metadados efetivamente presentes nesta amostra.

## Artefatos e reprodutibilidade

`strings-pointers.json`: strings qualificadas encontradas e ponteiros absolutos que as referenciam. `data-blocks.json`: evidência bruta selecionada. `selected-code.json`: wrappers e getters completos, RVAs/offsets/bytes. `getters-instructions.json`: inclui dois getters de outros registros de Transform (`0x3efbc0`, `0x3efb70`) para registrar que há múltiplos getters com mesmo nome simples; não foram atribuídos a IEntity. `direct-calls.json`: resultado vazio da busca validada de CALL direto. `negative-string-scan.json`: limites literais da busca. Scripts originais estão no scratch `work\spatial\`; usam RawPE/iced-x86 da V2 sem alterar esse módulo.
